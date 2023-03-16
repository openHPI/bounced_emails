import logging
import asyncore
import traceback
from smtpd import SMTPServer


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

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        try:
            for handler in self.handler:
                handler.handle_message(data)
        except:
            tb = traceback.format_exc()
            logger.error(tb)

    def handle_stop(self):
        raise asyncore.ExitNow('SMTP Server is quitting!')

    def register_handler(self, handler):
        self.handler.append(handler)
