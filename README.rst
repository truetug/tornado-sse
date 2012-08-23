===========
tornado-sse
===========

tornado-sse use `tornado <http://www.tornadoweb.org/>`_ and `brukva <https://github.com/evilkost/brukva>`_ for multichannel `Server-Sent Event <http://www.html5rocks.com/en/tutorials/eventsource/basics/>`_ server. Additional it provides such thins like: eventsource polyfill, we prefer `jQuery.eventsource <https://github.com/rwldrn/jquery.eventsource/>`_; javascript handler for delegate SSE to jQuery events; Django management command and special Django handler.

Installation
============

::

    pip install git+git://github.com/truetug/tornado-sse.git

Standalone
===========

Start server::

    $ tornado_sse [--address=127.0.0.1] [--port=8888] [--debug]

Then place static files to serve directory, or just map Nginx location to tornado_sse/static directory.

Client
------

To subscribe to some channels just place them to get parameter "channels" in "sse-data" attribute of body::

    <head>
        <script type="text/javascript" src="/media/tornado_sse/jquery.eventsource.js"></script>
        <script type="text/javascript" src="/media/tornado_sse/sse.js"></script>
    </head>

    <body sse-data="/sse/?channels=all,foo">
        ...
    </body>

Intercept events
----------------

Unfortunately, many browsers catch only "onopen" and "onmessage" event, so for now I decide to make my own format of JSON for different kinds of messages::

    // for redis 127.0.0.1:6379> PUBLISH all '["message", "{\"type\": \"message\", \"your-structure\": \"Blowjob is better than no job 1\", \"user\": \"tug\"}"]'
    $('body').on('sse.message', function(el, msg){
        console.log(msg);
    });

    // for redis 127.0.0.1:6379> PUBLISH all '["message", "{\"type\": \"foo\", \"other-structure\": \"Blowjob is better than no job 1\", \"user\": \"bar\"}"]'
    $('body').on('sse.foo', function(el, msg){
        console.log(msg);
    });

With Django
===========

Installation
------------

Install redis and django_sse. It is no requirements of tornado_sse.

Add "redis", "django_sse" and "tornado_sse" to INSTALLED_APPS::

    ### SSE ###
    INSTALLED_APPS += (
        'redis',
        'django_sse',
        'tornado_sse',
    )

    REDIS_SSEQUEUE_CONNECTION_SETTINGS = {
        'location': 'localhost:6379',
        'db': 0,
    }
    ### SSE ###

tornado_sse use same settings for connection to redis as django_sse.

Sending messages from Django
----------------------------

Handler for Django differs from usual handler. It subscribes to channels: "%username%" and "all".

To send message you may use send_event function from django_sse.redisqueue.

I prefer to use signals for such things. So for user with login "admin" it would look something like this::

    # encoding: utf-8
    from django.utils import simplejson as json
    from django.dispatch.dispatcher import receiver
    from django.db.models.signals import post_save

    from django_sse.redisqueue import send_event

    from myapp.models import MyModel


    @receiver(post_save, sender=MyModel)
    def mymodel_post_save_notify(sender, **kwargs):
        instance = kwargs.get('instance')

        message = json.dumps({
            'type': 'foo',
            'html': instance.as_html(),
        })

        send_event('message', message, 'admin') # named channel

        return True

Start server::

    (env) ...$ python manage.py runsseserver

Client
------

In HTML no need to register channels in "sse-data" because handler determines their names on the session::

    <head>
        <script type="text/javascript" src="{{ STATIC_URL }}tornado_sse/jquery.eventsource.js"></script>
        <script type="text/javascript" src="{{ STATIC_URL }}tornado_sse/sse.js"></script>
    </head>

    <body sse-data="/sse/">
        ...
    </body>


Intercept events
----------------

Use code from Standalone section.

Nginx setup
===========

If your main server in behind Nginx you may proxy SSE like this::

    location /sse/ {
        rewrite                 ^(.*)$ / break; # to root of our tornado
        proxy_buffering         off; # to push immediately
        proxy_pass              http://127.0.0.1:8888;
    }
