#!/usr/bin/env python
# encoding: utf-8

import os, sys
sys.path.insert(0, '/Users/tug/Work/projects/cdnmail.ru/website')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import tornado.web
import tornado.escape
import tornado.ioloop
import tornado.web

import django.conf
import django.contrib.auth
import django.core.handlers.wsgi
import django.db
import django.utils.importlib

from tornado.options import define, options
define('debug', default=False, help='Verbose output', type=bool)
define('port', default=8888, help='Run on the given port', type=int)

import brukva
CHANNEL = 'sse'

import json
from datetime import datetime
from time import time

from sse import Sse

import json
import time

import logging
formatter = logging.Formatter(fmt='%(asctime)s:%(levelname)s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(handler)

import hashlib
#from handler import SSEHandler


def send_message(msg=None):
    event, data = json.loads(msg.body)

    sse = Sse()
    sse.add_message(event, data)
    message = ''.join(sse)

    clients = MainHandler._channels.get(msg.channel, [])
    logger.debug('Sending %s "%s" to %s clients' % (event, data, len(clients)))
    logger.debug('Message:\n%s' % message)
    for x in clients:
        x.on_message(message)


class MainHandler(tornado.web.RequestHandler):
    _closing_timeout = False
    _connections = [] # Yes, this list is declared here because it is used by the class methods
    _channels = {}

    def initialize(self):
        self.set_status(200)
        self.set_header('Content-Type','text/event-stream; charset=utf-8')
        self.set_header('Cache-Control','no-cache')
        self.set_header('Connection','keep-alive')

    @tornado.web.asynchronous
    def get(self):
        cls = MainHandler

        headers = self._generate_headers()
        self.write(headers)
        self.flush()

        self.user = self.get_current_user()
        if not self.user:
            self.set_status(403)
            self.finish()
        else:
            self.connection_id = time.time()
            self.channel = self.user
            logger.debug('Incoming connection %s to channel "%s"' % (self.connection_id, self.channel))
            if not self.channel in cls._channels:
                if cls._channels.keys():
                    cls.client.unsubscribe(cls._channels.keys())

                cls._channels[self.channel] = set([self])
                cls.client.subscribe(cls._channels.keys())
                cls.client.listen(send_message)
                logger.debug('Channels: %s' % ', '.join(cls._channels.keys()))
            else:
                cls._channels[self.channel].add(self)

    def on_connection_close(self):
        cls = MainHandler
        logger.debug('Connection %s is closed' % self.connection_id)
        if len(cls._channels[self.channel]) > 1:
            cls._channels[self.channel].remove(self)
        else:
            del cls._channels[self.channel]
            logger.debug('Channels: %s' % ', '.join(cls._channels.keys()))

    def on_message(self, data=None):
        if data:
            self.write(data)
            self.flush()

    def get_django_session(self):
        if not hasattr(self, '_session'):
            engine = django.utils.importlib.import_module(django.conf.settings.SESSION_ENGINE)
            session_key = self.get_cookie(django.conf.settings.SESSION_COOKIE_NAME)
            self._session = engine.SessionStore(session_key)
        return self._session

    def get_current_user(self):
        """ get_user needs a django request object, but only looks at the session """
        class Dummy: pass

        django_request = Dummy()
        django_request.session = self.get_django_session()
        user = django.contrib.auth.get_user(django_request)
        return user.username if user.is_authenticated() else None


class Application(tornado.web.Application):
    periodic_callbacks = {}

    def __init__(self):
        handlers = [
            (r'/', MainHandler),
        ]

        settings = dict(
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            #template_path=os.path.join(os.path.dirname(__file__), "templates"),
            xsrf_cookies=True,
            autoescape=None,
            #login_url='http://127.0.0.1:8000/login/',
        )

        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    tornado.options.parse_command_line()
    #logger.setLevel(logging.DEBUG if options.debug else logging.INFO)
    if options.debug:
        logger.setLevel(logging.DEBUG)

    MainHandler.client = brukva.Client()
    MainHandler.client.connect()

    try:
        logger.info('Come along tornado on port %s...' % options.port)

        application = Application()
        application.listen(options.port)
        application.loop = tornado.ioloop.IOLoop.instance()

        application.loop.start()
    except KeyboardInterrupt, e:
        pass
    finally:
        MainHandler.client.disconnect()
        logger.info('Shutdowned')


if __name__ == '__main__':
    main()
