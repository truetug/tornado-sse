# encoding: utf-8
import tornado.web
import tornado.escape
import tornado.ioloop

import time
import json
import hashlib
import logging

import brukva
from sse import Sse


logger = logging.getLogger()


CHANNEL = 'sse'

SSE_HEADERS = (
    ('Content-Type','text/event-stream; charset=utf-8'),
    ('Cache-Control','no-cache'),
    ('Connection','keep-alive'),
)


class SSEHandler(tornado.web.RequestHandler):
    _closing_timeout = False
    _connections = []
    _channels = {}
    _source = None

    def __init__(self, application, request, **kwargs):
        super(SSEHandler, self).__init__(application, request, **kwargs)
        self.stream = request.connection.stream
        self._closed = False

    def initialize(self):
        for name, value in SSE_HEADERS:
            self.set_header(name, value)

    def get_class(self):
        return self.__class__

    def set_source(self):
        cls = self.__class__
        if not cls._source:
            cls._source = brukva.Client()
            cls._source.connect()

    def set_id(self):
        self.connection_id = hashlib.md5('%s-%s-%s' % (
            self.request.connection.address[0],
            self.request.connection.address[1],
            time.time(),
        )).hexdigest()

    def get_channel(self):
        return self.get_argument('channel', CHANNEL)

    @tornado.web.asynchronous
    def get(self):
        # Sending the standard headers: open event
        headers = self._generate_headers()
        self.write(headers)
        self.flush()

        self.set_id()
        self.channel = self.get_channel()
        if not self.channel:
            self.set_status(403)
            self.finish()
        else:
            self.on_open()

    def on_open(self, *args, **kwargs):
        """ Invoked for a new connection opened. """
        cls = self.__class__

        logger.info('Incoming connection %s to channel "%s"' % (self.connection_id, self.channel))
        self.set_source()

        if not self.channel in cls._channels:
            if cls._channels.keys():
                cls._source.unsubscribe(cls._channels.keys())

            cls._channels[self.channel] = [self]
            cls._source.subscribe(cls._channels.keys())
            cls._source.listen(cls.on_message)
            logger.debug('Channels: %s' % ', '.join(cls._channels.keys()))
        else:
            cls._channels[self.channel].append(self)

    def on_close(self):
        """ Invoked when the connection for this instance is closed. """
        cls = self.__class__

        logger.info('Connection %s is closed' % self.connection_id)
        if len(cls._channels[self.channel]) > 1:
            cls._channels[self.channel].remove(self)
        else:
            del cls._channels[self.channel]
            logger.debug('Channels: %s' % ', '.join(cls._channels.keys()))

    def on_connection_close(self):
        """ Closes the connection for this instance """
        logger.debug('Connection %s is closed, wait for 5 seconds' % self.connection_id)
        if not self._closed and not getattr(self, '_closing_timeout', None):
            self._closed = True
            self._closing_timeout = tornado.ioloop.IOLoop.instance().add_timeout(time.time() + 5, self._abort)
        else:
            tornado.ioloop.IOLoop.instance().remove_timeout(self._closing_timeout)

    def _abort(self):
        """ Instantly aborts the connection by closing the socket """
        self.on_close() # Calling the closing event
        self.stream.close()

    @classmethod
    def on_message(cls, msg):
        """ Sends a message to all live connections """
        event, data = json.loads(msg.body)

        sse = Sse()
        sse.add_message(event, data)
        message = ''.join(sse)

        clients = cls._channels.get(msg.channel, [])
        logger.debug('Sending %s "%s" to %s clients' % (event, data, len(clients)))
        for client in clients:
            client.write_message(message)

    def write_message(self, message):
        self.write(message)
        self.flush()


class DjangoSSEHandler(SSEHandler):
    @tornado.web.asynchronous
    def get_channel(self):
        user = self.get_current_user()
        return user.username if user else None

    def get_django_session(self):
        """ Gets django session """
        from django.utils.importlib import import_module
        from django.conf import settings

        if not hasattr(self, '_session'):
            engine = import_module(settings.SESSION_ENGINE)
            session_key = self.get_cookie(settings.SESSION_COOKIE_NAME)
            self._session = engine.SessionStore(session_key)

        return self._session

    def get_current_user(self):
        """ Gets user from request using django session engine """
        from django.contrib.auth import get_user

        # get_user needs a django request object, but only looks at the session
        class Dummy: pass

        django_request = Dummy()
        django_request.session = self.get_django_session()
        user = get_user(django_request)
        return user if user.is_authenticated() else None
