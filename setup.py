#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from codecs import open

from setuptools import setup

with open('splunksolutionlib/__init__.py', 'r') as fd:
    content = fd.read()
    title = re.search(r'^__title__\s*=\s*[\'"]([^\'"]*)[\'"]',
                      content, re.MULTILINE).group(1)
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        content, re.MULTILINE).group(1)
    release = re.search(r'^__release__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        content, re.MULTILINE).group(1)
    author = re.search(r'^__author__\s*=\s*[\'"]([^\'"]*)[\'"]',
                       content, re.MULTILINE).group(1)
    copyright = re.search(r'^__copyright__\s*=\s*[\'"]([^\'"]*)[\'"]',
                          content, re.MULTILINE).group(1)

if not title:
    raise RuntimeError("Cannot find title information")

if not version:
    raise RuntimeError("Cannot find version information")

if not release:
    raise RuntimeError("Cannot find release information")

if not author:
    raise RuntimeError("Cannot find author information")

if not copyright:
    raise RuntimeError("Cannot find copyright information")

packages = [
    'splunksolutionlib',
    'splunksolutionlib.common',
    'splunksolutionlib.platform'
]

install_requires = []

classifiers = (
    'Programming Language :: Python',
    'Development Status :: 1 - Alpha',
    'Environment :: Other Environment',
    'Intended Audience :: Developers',
    'Operating System :: OS Independent',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: Software Development :: Libraries :: Application Frameworks'
)

setup(
    name=title,
    version=version,
    description='The Splunk Software Development Kit for Solutions',
    author=author,
    author_email='Shanghai-TA-dev@splunk.com',
    url='https://git.splunk.com/scm/solnsc/lib-solutions-python.git',
    packages=packages,
    install_requires=install_requires,
    zip_safe=False,
    classifiers=classifiers
)
