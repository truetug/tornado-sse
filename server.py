#!/usr/bin/env python
# encoding: utf-8
import tornado.web
import tornado.escape
import tornado.ioloop
import tornado.web

from tornado.options import define, options
define('port', default=8888, help='Run on the given port', type=int)

import brukva
channel = 'sse'

import json
from datetime import datetime
from time import time

from sse import Sse
s = Sse()

import json
import time
import logging
import hashlib
#from handler import SSEHandler


def send_message(msg=None):
    #import pdb; pdb.set_trace()
    event, data = json.loads(msg.body)
    logging.info('Sending %s "%s" to %s clients' % (event, data, len(MySSEHandler._live_connections)))
    for x in MySSEHandler._live_connections:
        x.on_message(None, data)


class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        logging.info('Connection is established')
        self.write('Hello, world')

    def on_connection_close(self):
        logging.info('Connection is closed')


class MySSEHandler(tornado.web.RequestHandler):
    _closing_timeout = False
    _live_connections = [] # Yes, this list is declared here because it is used by the class methods

    @tornado.web.asynchronous
    def get(self):
        # Sending the standard headers
        headers = self._generate_headers()
        self.write(headers); self.flush()

        # Adding the current client instance to the live handlers pool
        #self.connection_id = self.generate_id()
        self.connection_id = time.time()
        MySSEHandler._live_connections.append(self)
        logging.info('Incoming connection: %s' % self.connection_id)

        # Calling the open event
        #self.on_open()

    def on_connection_close(self):
        logging.info('Connection %s is closed' % self.connection_id)
        del MySSEHandler._live_connections[self.connection_id]

    @tornado.web.asynchronous
    def on_message(self, id=None, data=None):
        if data:
            message = tornado.escape.utf8(
                'id: %s\ndata: %s\n\n' % (event_id if event_id else '',  data)
            )
            logging.info(message)
            self.write(message)
            self.flush()

    def send_message(self):
        logging.info('Sending new message')
        MessageSourceHandler.counter += 1
        MessageSourceHandler.write_message_to_all('message', {
            'waiters': len(MessageSourceHandler._live_connections),
            'counter': MessageSourceHandler.counter,
        })

        MessageSourceHandler._msg_timeout = tornado.ioloop.IOLoop.instance().add_timeout(time.time() + 5, self.send_message)


class Application(tornado.web.Application):
    periodic_callbacks = {}

    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            #(r"/sse-handler", MessageSourceHandler),
            #(r'/', MainHandler),
            (r'/sse/', MySSEHandler),
        ]

        settings = dict(
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            #template_path=os.path.join(os.path.dirname(__file__), "templates"),
            xsrf_cookies=True,
            autoescape=None,
        )

        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    tornado.options.parse_command_line()
    logging.info('Come along tornado on port %s...' % options.port)

    application = Application()
    application.listen(options.port)
    application.loop = tornado.ioloop.IOLoop.instance()

#    application.periodic_callbacks['test'] = tornado.ioloop.PeriodicCallback(send_message, 5000, application.loop)
#    application.periodic_callbacks['test'].start()

    application.loop.start()


if __name__ == '__main__':
    try:
        redis = brukva.Client()
        redis.connect()
        redis.subscribe(channel)
        redis.listen(send_message)
        main()
    except KeyboardInterrupt, e:
        pass
    finally:
        redis.disconnect()
        logging.info('Shutdowned')
