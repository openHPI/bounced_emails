# -*- coding: utf-8 -*-
import pika
import logging
from pprint import pprint
from handler import BouncedEmailException

logger = logging.getLogger('bouncedemails')


class Consumer(object):
    def __init__(self, settings, handler):
        self.settings = settings
        self.amqp_config = settings.config[settings.env]['amqp']
        self.handler = handler

    def _log(self, obj):
        if self.settings.debug:
            pprint(obj)

    def _callback(self, ch, method, properties, body):
        ch.basic_ack(delivery_tag=method.delivery_tag)
        try:
            self.handler.handle_message(body)
        except BouncedEmailException as e:
            logger.error('An exception occured: %s', e)

    def run(self):
        url = self.amqp_config['url']
        params = pika.URLParameters(url)
        params.socket_timeout = 5
        self.connection = pika.BlockingConnection(params)

        channel = self.connection.channel()
        channel.queue_declare(queue=self.amqp_config['queue'])
        channel.basic_consume(
            queue=self.amqp_config['queue'], on_message_callback=self._callback)
        channel.start_consuming()

    def stop(self):
        self.connection.close()
