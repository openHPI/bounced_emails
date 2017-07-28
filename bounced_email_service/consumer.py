# -*- coding: utf-8 -*-
import pika
from pprint import pprint


class Consumer(object):
    def __init__(self, settings, handler):
        self.settings = settings
        self.amqp_config = settings.config[settings.env]['amqp']
        self.handler = handler

    def _log(self, obj):
        if self.settings.debug:
            pprint(obj)

    def _callback(self, ch, method, properties, body):
        ch.basic_ack(delivery_tag = method.delivery_tag)
        self.handler.handle_message(body)

    def run(self):
        url = self.amqp_config['url']
        params = pika.URLParameters(url)
        params.socket_timeout = 5
        self.connection = pika.BlockingConnection(params)

        channel = self.connection.channel()
        channel.basic_consume(self._callback, queue=self.amqp_config['queue'])
        channel.start_consuming()

    def stop(self):
        self.connection.close()