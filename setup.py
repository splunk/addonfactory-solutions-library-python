#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from codecs import open

from setuptools import setup

with open('splunksolutionlib/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError("Cannot find version information")

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
    name='splunksolutionlib',
    version=version,
    description='The Splunk Software Development Kit for Solutions',
    author='Splunk, Inc.',
    author_email='Shanghai-TA-dev@splunk.com',
    url='https://git.splunk.com/scm/solnsc/lib-solutions-python.git',
    packages=packages,
    install_requires=install_requires,
    zip_safe=False,
    classifiers=classifiers
)
