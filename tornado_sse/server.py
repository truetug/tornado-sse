#!/usr/bin/env python
# encoding: utf-8
import tornado.web
import tornado.escape
import tornado.ioloop

import logging
formatter = logging.Formatter(fmt='%(asctime)s:%(levelname)s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(handler)

from tornado_sse.handlers import SSEHandler


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r'/', SSEHandler)]
        tornado.web.Application.__init__(self, handlers)


def main():
    try:
        logger.info('Come along tornado on %s:%s...' % (options.address, options.port))

        application = Application()
        application.listen(options.port, options.address)
        application.loop = tornado.ioloop.IOLoop.instance()

        application.loop.start()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info('Shutdowned')


if __name__ == '__main__':
    from tornado.options import define, options
    define('debug', default=False, help='Verbose output', type=bool)
    define('port', default=8888, help='Run on the given port', type=int)
    define('address', default='127.0.0.1', help='Bind to given address', type=str)

    tornado.options.parse_command_line()
    if options.debug: logger.setLevel(logging.DEBUG)

    main()
