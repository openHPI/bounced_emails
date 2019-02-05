# -*- coding: utf-8 -*-
import os
import sys
import yaml
import click

from bounced_email_service.consumer import Consumer
from bounced_email_service.handler import Handler


class BouncedEmailSettings(object):
    def __init__(self, env, debug):
        self.env = env
        self.debug = debug
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.config = yaml.load(
            open(os.path.join(self.project_root, 'config.yml')).read())


@click.group()
@click.option('--env', default='production', help='environment')
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def cli(ctx, env, debug):
    """Bounced Email Service"""
    ctx.obj = BouncedEmailSettings(env, debug)


@cli.command()
@click.option('--bounced_address', required=True, help='bounced address')
@click.option('--domain', required=True, help="domain")
@click.pass_context
def set_permanent_bounced_address(ctx, bounced_address, domain):
    """Set an email address as permanent failure"""
    handler = Handler(ctx.obj)
    handler.set_permanent_bounced_address(bounced_address, domain)


@cli.command()
@click.option('--address', required=True, help='email address')
@click.pass_context
def find_address(ctx, address):
    """Find an email address within permanent or temporary bounced emails"""
    handler = Handler(ctx.obj)
    handler.find_address(address)


@cli.command()
@click.pass_context
def stdin(ctx):
    """Get email for Bounced Email Service from stdin"""
    lines = sys.stdin.readlines()
    body = "".join(lines).strip().encode('utf-8')
    handler = Handler(ctx.obj)
    handler.handle_message(body)


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
