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
    _connections = {}
    _channels = {}
    _stored_channels = []
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

    def get_channels(self):
        result = self.get_argument('channels', CHANNEL)
        result = [x.strip() for x in result.split(',') if x]
        return result

    def subscribe(self):
        cls = self.__class__
        schs = set(cls._channels.keys())
        uchs = set(cls._stored_channels)

        if schs != uchs:
            # Unsubscribe from all channels
            chs = uchs.difference(schs)
            if chs:
                cls._source.unsubscribe(chs)

            # Subscribe to new channels
            chs = schs.difference(uchs)
            if chs:
                cls._source.subscribe(chs)
                cls._source.listen(cls.send_message)

            logger.debug('Channels: %s' % ', '.join(schs))
            cls._stored_channels = schs

    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        # Sending the standard headers: open event
        headers = self._generate_headers()
        self.write(headers)
        self.flush()

        self.set_id()
        self.channels = self.get_channels()
        if not self.channels:
            self.set_status(403)
            self.finish()
        else:
            self.on_open()

    def on_open(self, *args, **kwargs):
        """ Invoked for a new connection opened. """
        cls = self.__class__

        logger.info('Incoming connection %s to channels "%s"' % (self.connection_id, ', '.join(self.channels)))
        cls._connections[self.connection_id] = self
        self.set_source()

        # Bind channels
        for channel in self.channels:
            if channel not in cls._channels:
                cls._channels[channel] = []

            cls._channels[channel].append(self.connection_id)

        self.subscribe()

    def on_close(self):
        """ Invoked when the connection for this instance is closed. """
        cls = self.__class__

        logger.info('Connection %s is closed' % self.connection_id)
        del cls._connections[self.connection_id]

        for channel in self.channels:
            if len(cls._channels[channel]) > 1:
                cls._channels[channel].remove(self.connection_id)
            else:
                del cls._channels[channel]

        self.subscribe()

    def on_connection_close(self):
        """ Closes the connection for this instance """
        self.on_close()
        self.stream.close()

    @classmethod
    def send_message(cls, msg):
        """ Sends a message to all live connections """
        event, data = json.loads(msg.body)

        sse = Sse()
        sse.add_message(event, data)
        message = ''.join(sse)

        clients = cls._channels.get(msg.channel, [])
        logger.debug('Sending %s "%s" to channel %s for %s clients' % (event, data, msg.channel, len(clients)))
        for client_id in clients:
            client = cls._connections[client_id]
            client.on_message(message)

    def on_message(self, message):
        self.write(message)
        self.flush()


class DjangoSSEHandler(SSEHandler):
    @tornado.web.asynchronous
    def get_channels(self):
        user = self.get_current_user()
        return ['all', user.username] if user else None

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
