# -*- coding: utf-8 -*-
import os
import re
import gzip
import email
import sqlite3
import requests
import tldextract

from datetime import datetime
from email.utils import parseaddr
from uritemplate import URITemplate
from flufl.bounce import all_failures
from cachecontrol import CacheControl
from validate_email import validate_email


class Handler(object):
    def __init__(self, settings):
        self.settings = settings
        self.handler_config = settings.config[settings.env]['handler']
        self.cached_session = CacheControl(requests.session())

        self._init_db()

    def _log(self, obj):
        if self.settings.debug:
            print(obj)

    def _get_db_conn(self):
        return sqlite3.connect(self.handler_config['dbfile'])

    def _init_db(self):
        con = self._get_db_conn()
        cur = con.cursor()
        stmt = '''
        CREATE TABLE IF NOT EXISTS temporary_bounces
            (
                bounced_address TEXT,
                domain TEXT,
                counter INTEGER
            );
        '''
        cur.execute(stmt.strip())
        con.commit()

        stmt = '''
        CREATE TABLE IF NOT EXISTS permanent_bounces
            (
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bounced_address TEXT,
                domain TEXT,
                status_code INTEGER
            );
        '''
        cur.execute(stmt.strip())
        con.commit()

        cur.close()
        con.close()

    def _increase_bounced_address_counter(self, bounced_address, domain):
        con = self._get_db_conn()
        cur = con.cursor()
        stmt = '''
        INSERT OR REPLACE INTO temporary_bounces
            VALUES (:bounced_address, :domain,
            COALESCE(
                (SELECT counter FROM temporary_bounces
                    WHERE bounced_address=:bounced_address AND domain=:domain),
                0) + 1);
        '''
        cur.execute(stmt.strip(), {'bounced_address': bounced_address, 'domain': domain})
        con.commit()

        cur.close()
        con.close()

    def _get_bounced_address_counter(self, bounced_address, domain):
        con = self._get_db_conn()
        cur = con.cursor()
        stmt = '''
        SELECT counter FROM temporary_bounces
            WHERE bounced_address=:bounced_address AND domain=:domain;
        '''
        cur.execute(stmt.strip(), {'bounced_address': bounced_address, 'domain': domain})
        row = cur.fetchone()
        result = 0
        if row:
            result = int(row[0])

        cur.close()
        con.close()
        return result

    def _find_address(self, address):
        con = self._get_db_conn()
        cur = con.cursor()
        stmt = '''
        SELECT * FROM permanent_bounces
            WHERE bounced_address LIKE :bounced_address;
        '''
        cur.execute(stmt.strip(), {'bounced_address': '%{0}%'.format(address)})
        permanent_bounces = cur.fetchall()

        stmt = '''
        SELECT * FROM temporary_bounces
            WHERE bounced_address LIKE :bounced_address;
        '''
        cur.execute(stmt.strip(), {'bounced_address': '%{0}%'.format(address)})
        temporary_bounces = cur.fetchall()

        cur.close()
        con.close()
        return permanent_bounces, temporary_bounces


    def _reset_bounced_address(self, bounced_address, domain):
        con = self._get_db_conn()
        cur = con.cursor()
        stmt = '''
        DELETE FROM temporary_bounces
            WHERE bounced_address=:bounced_address AND domain=:domain;
        '''
        cur.execute(stmt.strip(), {'bounced_address': bounced_address, 'domain': domain})
        con.commit()

        cur.close()
        con.close()

    def _set_permanent_bounced_address(self, bounced_address, domain, status_code):
        con = self._get_db_conn()
        cur = con.cursor()
        stmt = '''
        INSERT INTO permanent_bounces (bounced_address, domain, status_code)
            VALUES (:bounced_address, :domain, :status_code);
        '''
        cur.execute(stmt.strip(), {
            'bounced_address': bounced_address,
            'domain': domain,
            'status_code': status_code
        })
        con.commit()

        cur.close()
        con.close()

    def _get_origin_to_domains(self, msg):
        '''
        return the domains to which the origin email was sent
        '''
        to_addresses = [address for _, address in [parseaddr(x.strip()) for x in msg['To'].split(",")]]
        domains = []
        for a in to_addresses:
            parts = tldextract.extract(a.split("@")[1])
            domains.append("%s.%s" % (parts[-2], parts[-1]))
        return domains

    def _store_permanent_bounced_email(self, bounced_address, body):
        if not ('permanent_bounced_emails_path' in self.handler_config and body):
            return

        dir_path = os.path.join(
            self.handler_config['permanent_bounced_emails_path'],
            bounced_address[0:2].lower())

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        path = os.path.join(dir_path, bounced_address + '.gz')
        content = bytes(body)
        with gzip.open(path, 'wb') as f:
            f.write(content)

    def _handle_out_of_office_message(self, msg):
        pass

    def _handle_temporary_bounced_address(self, bounced_address, domain, body):
        temporary_threshold = self.handler_config['temporary_threshold']
        current_counter = self._get_bounced_address_counter(bounced_address, domain)

        if current_counter > temporary_threshold:
            self._handle_permanent_bounced_address(bounced_address, domain, body)
            self._reset_bounced_address(bounced_address, domain)
            return

        self._increase_bounced_address_counter(bounced_address, domain)

    def _handle_permanent_bounced_address(self, bounced_address, domain, body):
        config = self.handler_config['domains'][domain]        

        response = self.cached_session.get(config['base_url'])
        uri = response.json()['email_suspensions_url']
        tpl = URITemplate(uri)
        endpoint = tpl.expand(address=bounced_address)

        self._log("Post request to: %s for address: %s" % (endpoint, bounced_address))

        response = self.cached_session.post(endpoint, data={})
        self._log("Response text: %s" % response.text)

        self._set_permanent_bounced_address(bounced_address, domain, response.status_code)
        self._store_permanent_bounced_email(bounced_address, body)

    def set_permanent_bounced_address(self, bounced_address, domain):
        '''
        handles manually bounced email addresses
        '''
        self._log("Permanent: %s" % bounced_address)
        self._handle_permanent_bounced_address(bounced_address, domain, '')

    def find_address(self, address):
        '''
        Find an email address within permanent or temporary bounced emails
        '''
        self._log("Find: %s" % address)
        permanent_bounces, temporary_bounces = self._find_address(address)

        print('> Permanent bounces for address: "{0}"'.format(address))
        for entry in permanent_bounces:
            print(entry)
        
        print('> Temporary bounces for address: "{0}"'.format(address))
        for entry in temporary_bounces:
            print(entry)

    def handle_message(self, body):
        '''
        handles soft and hard bounced emails
        '''
        msg = email.message_from_bytes(bytes(body))
        self._log("------------- INCOMING MESSAGE -------------")
        for key, value in msg.items():
            self._log("%s:\t%s" % (key, value))
        self._log("")

        t, p = all_failures(msg)

        def validate_addresses(bounced_addresses):
            address_list = []
            for address in bounced_addresses:
                address = address.decode('utf-8')
                if validate_email(address):
                    address_list.append(address)
            return address_list

        temporary = validate_addresses(t)
        permanent = validate_addresses(p)

        if not (temporary or permanent):
            return self._handle_out_of_office_message(msg)

        for domain in self._get_origin_to_domains(msg):
            if domain in self.handler_config['domains'].keys():
                break
        else:
            raise Exception("Domain '%s' not found" % domain)

        self._log("Domain: %s" % domain)

        for bounced_address in temporary:
            # sometimes a temporary failure is a permanent failure as well (strange, but yes)
            if bounced_address in permanent:
                continue
            self._log("Temporary: %s" % bounced_address)
            self._handle_temporary_bounced_address(bounced_address, domain, body)

        for bounced_address in permanent:
            self._log("Permanent: %s" % bounced_address)
            self._handle_permanent_bounced_address(bounced_address, domain, body)
