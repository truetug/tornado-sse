#!/usr/bin/env python
# encoding: utf-8

try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup


setup (
    name='tornado-sse',
    version='0.5.0',
    author='Sergey Trofimov',
    author_email='truetug@gmail.com',
    url='https://github.com/truetug/tornado-sse',
    description='Eventsource server on tornado: django support, channels, last-event-id, etc',
    long_description=open('README.txt', 'r').read(),
    packages=['tornado_sse',],
    zip_safe=False,
    requires=[],
    install_requires=[
        'tornado >= 2',
        'brukva',
    ],
    entry_points={
        'console_scripts': [
            'tornado_sse = tornado_sse.server:main',
        ],
    },
)