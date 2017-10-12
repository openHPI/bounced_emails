import mock
import yaml
import unittest

from bounced_email_service.handler import Handler


class TestHandleMessage(unittest.TestCase):

    @mock.patch('bounced_email_service.handler.os.makedirs', mock.Mock())
    @mock.patch('bounced_email_service.suspender.CacheControl')
    @mock.patch('bounced_email_service.handler.sqlite3')
    @mock.patch('bounced_email_service.handler.gzip')
    @mock.patch('bounced_email_service.handler.all_failures')
    def test_handle_message(self, all_failures, gzip, sqlite3, CacheControl):
        settings = mock.Mock()
        settings.env = 'test'
        settings.config = yaml.load('''
        test:
            handler:
                dbfile: /tmp/bounced_emails.db
                permanent_bounced_emails_path: /tmp/permanent_bounced_emails
                temporary_threshold: 3
            suspender:
                opensap.info:
                    base_url: http://127.0.0.1:7001
                openhpi.de:
                    base_url: http://127.0.0.1:7001
                mydomain.de:
                    base_url: http://mydomain.de/emails/suspend/
        ''')

        cursor = mock.Mock()
        conn = mock.Mock()
        conn.cursor.return_value = cursor
        sqlite3.connect.return_value = conn

        cursor.fetchone.return_value = ['1']

        cached_session = mock.Mock()
        CacheControl.return_value = cached_session

        handler = Handler(settings)
        body = str(
            "From: test@domain.de\n" +
            "To: no-reply@openhpi.de\n"
        ).encode('utf-8')

        all_failures.return_value = (
            [b'temporary1@domain.de', b'temporary2@domain.de'],
            [b'permanent1@domain.de', b'permanent2@domain.de'])

        response = mock.Mock()
        response.json.return_value = {"email_suspensions_url": "http://127.0.0.1:7001/emails/{address}/suspend"}
        response._status_code = 200

        cached_session.get.return_value = response
        cached_session.post.return_value = response

        handler.handle_message(body)

        ### So was wollen wir eigentl. alles abtesten? (Nur das wichtigste)

        # die beiden permanenten werden suspended
        # zunaechst die API Abfrage
        self.assertEqual([
            mock.call('http://127.0.0.1:7001'),
            mock.call('http://127.0.0.1:7001')],
            cached_session.get.call_args_list)
        # der suspend post request
        self.assertEqual([
            mock.call('http://127.0.0.1:7001/emails/permanent1%2540domain.de/suspend', data={}),
            mock.call('http://127.0.0.1:7001/emails/permanent2%2540domain.de/suspend', data={})],
            cached_session.post.call_args_list)

        # die beiden temporaeren werden abgefragt und inkrementiert
        self.assertTrue('SELECT counter FROM temporary_bounces' in cursor.execute.call_args_list[2][0][0])
        self.assertTrue('INSERT OR REPLACE INTO temporary_bounces' in cursor.execute.call_args_list[3][0][0])

        self.assertTrue('SELECT counter FROM temporary_bounces' in cursor.execute.call_args_list[4][0][0])
        self.assertTrue('INSERT OR REPLACE INTO temporary_bounces' in cursor.execute.call_args_list[5][0][0])

        # die beiden permanenten werden in die db eingetragen
        self.assertTrue('INSERT INTO permanent_bounces' in cursor.execute.call_args_list[6][0][0])
        self.assertTrue('INSERT INTO permanent_bounces' in cursor.execute.call_args_list[7][0][0])

        # schliesslich werden die beiden permanenten ins Dateisystem geschrieben
        self.assertEqual([
            mock.call('/tmp/permanent_bounced_emails/pe/permanent1@domain.de.gz', 'wb'),
            mock.call('/tmp/permanent_bounced_emails/pe/permanent2@domain.de.gz', 'wb')],
            gzip.open.call_args_list)
