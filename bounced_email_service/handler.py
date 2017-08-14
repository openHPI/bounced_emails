# -*- coding: utf-8 -*-
import re
import email
import sqlite3
import requests
import tldextract

from email.utils import parseaddr
from flufl.bounce import all_failures
from validate_email import validate_email


class Handler(object):
    def __init__(self, settings):
        self.settings = settings
        self.handler_config = settings.config[settings.env]['handler']
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

    def _handle_out_of_office_message(self, msg):
        pass

    def _handle_temporary_bounced_address(self, bounced_address, domain):
        temporary_threshold = self.handler_config['temporary_threshold']
        current_counter = self._get_bounced_address_counter(bounced_address, domain)

        if current_counter > temporary_threshold:
            self._handle_permanent_bounced_address(bounced_address, domain)
            self._reset_bounced_address(bounced_address, domain)
            return

        self._increase_bounced_address_counter(bounced_address, domain)

    def _handle_permanent_bounced_address(self, bounced_address, domain):
        config = self.handler_config['domains'][domain]
        r = requests.put(config['endpoint'], data = {'bounced_address': bounced_address})
        self._set_permanent_bounced_address(bounced_address, domain, r.status_code)

    def set_permanent_bounced_address(self, bounced_address, domain):
        self._log("Permanent: %s" % bounced_address)
        self._handle_permanent_bounced_address(bounced_address, domain)

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
            raise Exception("Domain not found")

        self._log("Domain: %s" % domain)

        for bounced_address in temporary:
            # sometimes a temporary failure is a permanent failure as well (strange, but yes)
            if bounced_address in permanent:
                continue
            self._log("Temporary: %s" % bounced_address)
            self._handle_temporary_bounced_address(bounced_address, domain)

        for bounced_address in permanent:
            self._log("Permanent: %s" % bounced_address)
            self._handle_permanent_bounced_address(bounced_address, domain)
