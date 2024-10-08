# -*- coding: utf-8 -*-
import os
import re
import gzip
import email
import logging
import sqlite3
import requests
import tldextract

from email.utils import parseaddr
from email.header import decode_header
from uritemplate import URITemplate
from flufl.bounce import all_failures
from cachecontrol import CacheControl
from validate_email import validate_email


logger = logging.getLogger('bouncedemails')


class BouncedEmailException(Exception):
    pass


class Handler(object):
    def __init__(self, settings):
        self.settings = settings
        self.handler_config = settings.config[settings.env]['handler']
        self.cached_session = CacheControl(requests.session())

        self._init_db()

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
        cur.execute(stmt.strip(), {
                    'bounced_address': bounced_address, 'domain': domain})
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
        cur.execute(stmt.strip(), {
                    'bounced_address': bounced_address, 'domain': domain})
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
        cur.execute(stmt.strip(), {
                    'bounced_address': bounced_address, 'domain': domain})
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
        to_addresses = [address for _, address in [
            parseaddr(x.strip()) for x in msg['To'].split(",")]]
        domains = []
        for a in to_addresses:
            extractResult = tldextract.extract(a.split("@")[1])
            domains.append(extractResult.registered_domain)
        return domains

    def _store_permanent_bounced_email(self, bounced_address, mail):
        if not ('permanent_bounced_emails_path' in self.handler_config):
            return

        dir_path = os.path.join(
            self.handler_config['permanent_bounced_emails_path'],
            bounced_address[0:2].lower())

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        path = os.path.join(dir_path, bounced_address + '.gz')
        content = bytes(mail)
        with gzip.open(path, 'wb') as f:
            f.write(content)

    def _handle_out_of_office_message(self, msg):
        logger.info(f'{"No action:":<11}out of office message')

    def _handle_temporary_bounced_address(self, bounced_address, domain, mail):
        temporary_threshold = self.handler_config['temporary_threshold']
        current_counter = self._get_bounced_address_counter(
            bounced_address, domain)

        if current_counter > temporary_threshold:
            self._handle_permanent_bounced_address(
                bounced_address, domain, mail)
            self._reset_bounced_address(bounced_address, domain)
            return

        self._increase_bounced_address_counter(bounced_address, domain)

    def _default_url_resolver(self, bounced_address, config):
        tpl = URITemplate(config['base_url'])
        return tpl.expand(address=bounced_address)

    def _xikolo_url_resolver(self, bounced_address, config):
        response = self.cached_session.get(config['base_url'])
        uri = response.json()['email_suspensions_url']
        tpl = URITemplate(uri)
        return tpl.expand(address=bounced_address)

    def _handle_permanent_bounced_address(self, bounced_address, domain, mail):
        config = self.handler_config['domains'][domain]

        if 'url_resolver' in config and config['url_resolver'] == 'xikolo':
            endpoint = self._xikolo_url_resolver(bounced_address, config)
        else:
            endpoint = self._default_url_resolver(bounced_address, config)

        logger.debug(f'{"Post to:":<11}{endpoint} - {bounced_address}')

        response = self.cached_session.post(endpoint, data={})
        logger.info(f'{"Response:":<11}{response.status_code}, {response.text}')

        self._set_permanent_bounced_address(
            bounced_address, domain, response.status_code)
        self._store_permanent_bounced_email(bounced_address, mail)

    def set_permanent_bounced_address(self, bounced_address, domain):
        '''
        handles manually bounced email addresses
        '''
        logger.debug(f'{"Permanent:":<11}{bounced_address}')
        self._handle_permanent_bounced_address(bounced_address, domain, '')

    def find_address(self, address):
        '''
        Find an email address within permanent or temporary bounced emails
        '''
        logger.debug(f'{"Find:":<11}{address}')
        permanent_bounces, temporary_bounces = self._find_address(address)

        logger.debug(f'> Permanent bounces for address: "{address}"')
        for entry in permanent_bounces:
            logger.debug(entry)

        logger.debug(f'> Temporary bounces for address: "{address}"')
        for entry in temporary_bounces:
            logger.debug(entry)

    def handle_message(self, mail):
        '''
        handles soft and hard bounced emails
        '''
        msg = email.message_from_bytes(bytes(mail))
        logger.info("------------- INCOMING MESSAGE -------------")
        for key, value in msg.items():
            if any(key.startswith(h) for h in ['From', 'To', 'Subject']):
                key += ':'
                decoded_header = decode_header(value)[0]
                if decoded_header[1]:
                    value = decoded_header[0].decode(decoded_header[1])
                logger.info(f'{key:<11}{value}')

        for domain in self._get_origin_to_domains(msg):
            if domain in self.handler_config['domains'].keys():
                break
        else:
            raise BouncedEmailException(f"Domain '{domain}' not found")

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

        logger.info(f'{"Domain:":<11}{domain}')

        for bounced_address in temporary:
            # sometimes a temporary failure is a permanent failure as well (strange, but yes)
            if bounced_address in permanent:
                continue
            logger.info("Temporary: %s", bounced_address)
            self._handle_temporary_bounced_address(
                bounced_address, domain, mail)

        for bounced_address in permanent:
            logger.info("Permanent: %s", bounced_address)
            self._handle_permanent_bounced_address(
                bounced_address, domain, mail)
