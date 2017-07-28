# -*- coding: utf-8 -*-
import pika


class Consumer(object):
    def __init__(self, settings, handler):
        self.amqp_config = settings.config[settings.env]['amqp']
        self.handler = handler

    def callback(self, ch, method, properties, body):
        if self.handler.check_message(body):
            ch.basic_ack(delivery_tag=method.delivery_tag)
        self.handler.handle_message(body)

    def run(self):
        url = self.amqp_config['url']
        params = pika.URLParameters(url)
        params.socket_timeout = 5
        self.connection = pika.BlockingConnection(params)

        channel = self.connection.channel()
        channel.basic_consume(
            self.callback, 
            queue=self.amqp_config['queue'], 
            no_ack=self.amqp_config['no_ack'])

        channel.start_consuming()

    def stop(self):
        self.connection.close()