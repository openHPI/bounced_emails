import logging
import asyncore
import traceback
from smtpd import SMTPServer
from handler import BouncedEmailException


logger = logging.getLogger()


class EmailServer(SMTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = []
        self.config = None

    def set_config(self, config):
        self.config = config

    def run(self):
        asyncore.loop()

    def process_message(self, peer, mailfrom, rcpttos, mail, **kwargs):
        try:
            for handler in self.handler:
                try:
                    handler.handle_message(mail)
                except BouncedEmailException as e:
                    logger.error('An exception occured: %s', e)
        except:
            tb = traceback.format_exc()
            logger.error(tb)

    def handle_stop(self):
        raise asyncore.ExitNow('SMTP Server is quitting!')

    def register_handler(self, handler):
        self.handler.append(handler)
