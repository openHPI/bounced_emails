# -*- coding: utf-8 -*-
import os
import yaml
import click

from .consumer import Consumer
from handler import Handler


class BouncedEmailSettings(object):
    def __init__(self, env):
        self.env = env
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.config = yaml.load(
            open(os.path.join(self.project_root, 'config.yml')).read())


@click.group()
@click.option('--env', default='develop', help='environment')
@click.pass_context
def cli(ctx, env):
    """Bounced Email Service"""
    ctx.obj = BouncedEmailSettings(env)


@cli.command()
@click.pass_context
def run(ctx):
    """Run Bounced Email Service"""
    try:
        handler = BouncedEmailHandler(ctx.obj)
        consumer = Consumer(ctx.obj)
        consumer.run()
    except KeyboardInterrupt:
        consumer.stop()

def main():
    cli(obj={})
