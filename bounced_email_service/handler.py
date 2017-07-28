# -*- coding: utf-8 -*-
import re
import email
import sqlite
import tldextract

from email.utils import parseaddr
from flufl.bounce import all_failures


class Handler(object):
    def __init__(self, settings):
        self.setttings = settings
        self.handler_config = settings.config[settings.env]['handler']
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

        CREATE TABLE IF NOT EXISTS permanent_bounces 
            (
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                bounced_address TEXT,
                domain TEXT,
                reporting_mta TEXT,
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
            VALUES (:bounced_address, :domain, :counter,
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
        result = int(cur.fetchone()[0])

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

    def _set_permanent_bounced_address(self, bounced_address, domain, reporting_mta, status_code):
        con = self._get_db_conn()
        cur = con.cursor()
        stmt = '''
        INSERT INTO permanent_bounces (bounced_address, domain, reporting_mta, status_code)
            VALUES (:bounced_address, :domain, :reporting_mta, :status_code);
        '''
        cur.execute(stmt.strip(), {
            'bounced_address': bounced_address,
            'domain': domain,
            'reporting_mta': reporting_mta,
            'status_code': status_code
        })
        con.commit()

        cur.close()
        con.close()

    def _get_reporting_mta(self, msg):
        m = re.match('from ([a-z0-9.-]+)', msg['Received'])
        if m and m.group(1):
            return m.group(1)

        _, from_addr = parseaddr(msg["From"])
        if from_addr:
            parts = tldextract.extract(from_addr.split("@")[1])
            return "%s.%s" % (parts[-2], parts[-1])

        _, return_path_addr = parseaddr(msg["Return-Path"])
        if return_path_addr:
            parts = tldextract.extract(return_path_addr.split("@")[1])
            return "%s.%s" % (parts[-2], parts[-1])

    def _get_origin_to_domains(msg):
        '''
        return the domains to which the origin email was sent
        '''
        to_addresses = [address for _, address in [parseaddr(x.strip()) for x in msg['To'].split(",")]]
        domains = []
        for a in to_addresses:
            parts = tldextract.extract(a.split("@")[1])
            domains.append("%s.%s" % (parts[-2], parts[-1]))
        return domains

    def _handle_out_of_office_message(msg):
        pass

    def _handle_temporary_bounced_address(self, bounced_address, domain, reporting_mta):
        temporary_threshold = self.handler_config['temporary_threshold']
        current_counter = self._get_bounced_address_counter(bounced_address, domain)

        if current_counter > temporary_threshold:
            self._handle_permanent_bounced_address(bounced_address, domain, reporting_mta)
            self._reset_bounced_address(bounced_address, domain)
            return

        self._increase_bounced_address_counter(bounced_address, domain)

    def _handle_permanent_bounced_address(self, bounced_address, domain, reporting_mta):
        config = self.handler_config['domains'][domain]
        r = requests.put(config['endpoint'], data = {'bounced_address': bounced_address})
        self._set_permanent_bounced_address(bounced_address, domain, reporting_mta, r.status_code)


    def check_message(self, body):
        try:
            return email.message_from_bytes(bytes(txt))['From']
        except:
            return False

    def handle_message(self, body):
        # we expect an email body
        msg = email.message_from_bytes(bytes(txt))

        temporary, permanent = all_failures(msg)
        if not (temporary and permanent):
            return _handle_out_of_office_message(msg)

        # do we need this really?
        reporting_mta = self._get_reporting_mta(msg)

        for domain in _get_origin_to_domains(msg):
            if domain in self.handler_config['domains'].keys():
                break
        else:
            raise Exception("Domain not found")

        for bounced_address in temporary:
            # sometimes a temporary failure is a permanent failure as well (strange, but yes)
            if bounced_address in permanent:
                continue
            self._handle_temporary_bounced_address(bounced_address, domain, reporting_mta)

        for bounced_address in permanent:
            self._handle_permanent_bounced_address(bounced_address, domain, reporting_mta)
