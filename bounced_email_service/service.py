# -*- coding: utf-8 -*-
import os
import yaml
import click

from .consumer import Consumer
from .handler import Handler


class BouncedEmailSettings(object):
    def __init__(self, env, debug):
        self.env = env
        self.debug = debug
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.config = yaml.load(
            open(os.path.join(self.project_root, 'config.yml')).read())


@click.group()
@click.option('--env', default='develop', help='environment')
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def cli(ctx, env, debug):
    """Bounced Email Service"""
    ctx.obj = BouncedEmailSettings(env, debug)


@cli.command()
@click.pass_context
def run(ctx):
    """Run Bounced Email Service"""
    try:
        handler = Handler(ctx.obj)
        consumer = Consumer(ctx.obj, handler)
        consumer.run()
    except KeyboardInterrupt:
        consumer.stop()

def main():
    cli(obj={})
