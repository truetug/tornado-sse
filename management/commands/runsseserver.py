# encoding: utf-8
import tornado.web
import tornado.escape
import tornado.ioloop

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django import get_version
from optparse import make_option

import os, sys

import logging
#formatter = logging.Formatter(fmt='%(asctime)s:%(levelname)s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
#handler = logging.StreamHandler()
#handler.setFormatter(formatter)

logger = logging.getLogger('django')
#logger.addHandler(handler)


### TORNADO ###
from tornado_sse.handlers import DjangoSSEHandler

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r'/', DjangoSSEHandler)]
        tornado.web.Application.__init__(self, handlers)


### DJANGO ###
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--address',
            dest = 'address',
            default = '127.0.0.1',
            help = 'Bind to given address',
        ),
        make_option(
            '--port',
            dest = 'port',
            default = '8888',
            help = 'Run on the given port',
        ),
        make_option(
            '--debug',
            action = 'store_true',
            dest = 'debug',
            default = False,
            help = 'Verbose output',
        ),

    )
    help = 'Starts a Tornado EventSource Server'
    args = '[optional port number, or ipaddr:port]'

    def handle(self, *args, **options):
        try:
            if options['debug']:
                logger.setLevel(logging.DEBUG)

            logger.info('Come along tornado on %s:%s...' % (options['address'], options['port']))

            #settings.REDIS_SSEQUEUE_CONNECTION_SETTINGS['location']
            #settings.REDIS_SSEQUEUE_CONNECTION_SETTINGS['db']

            application = Application()
            application.listen(options['port'], options['address'])
            application.loop = tornado.ioloop.IOLoop.instance()

            application.loop.start()
        except KeyboardInterrupt:
            pass
        finally:
            logger.info('Shutdowned')
