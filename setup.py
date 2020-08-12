#!/usr/bin/env python
#
# Copyright 2016 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re
import os.path as op
from setuptools import setup, Command, find_packages
import versioneer

with open('solnlib/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Cannot find version information')


class TestCommand(Command):
    '''
    Command to run the whole test suite.
    '''
    description = 'Run full test suite.'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pytest
        tests_dir = op.sep.join([op.dirname(op.abspath(__file__)), 'tests'])
        pytest.main(['-v', tests_dir])


class JTestCommand(Command):
    '''
    Command to run the whole test suite with junit report.
    '''
    description = 'Run full test suite with junit report.'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pytest
        tests_dir = op.sep.join([op.dirname(op.abspath(__file__)), 'tests'])
        pytest.main(['-v', '--junitxml=junit_report.xml', tests_dir])


class CoverageCommand(Command):
    '''
    Command to run the whole coverage.
    '''
    description = 'Run full coverage.'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pytest

        tests_dir = op.sep.join([op.dirname(op.abspath(__file__)), 'tests'])
        pytest.main(['-v', '--cov=solnlib', tests_dir])


class CoverageHtmlCommand(Command):
    '''
    Command to run the whole coverage.
    '''
    description = 'Run full coverage.'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pytest

        tests_dir = op.sep.join([op.dirname(op.abspath(__file__)), 'tests'])
        pytest.main(['-v', '--cov=solnlib', '--cov-report=html', tests_dir])


setup(
    name='solnlib',

    description='The Splunk Software Development Kit for Splunk Solutions',

    author='Splunk, Inc.',

    author_email='Shanghai-TA-dev@splunk.com',

    license='http://www.apache.org/licenses/LICENSE-2.0',

    url='https://git.splunk.com/scm/solnsc/lib-solutions-python.git',

    packages=find_packages(exclude=['tests', 'examples']),

    package_data={'': ['LICENSE']},

    install_requires=[
        'requests'
    ],
    version=versioneer.get_version(),
    cmdclass={'test': TestCommand,
              'jtest': JTestCommand,
              'cov': CoverageCommand,
              'cov_html': CoverageHtmlCommand},

    classifiers=[
        'Programming Language :: Python',
        "Development Status :: 6 - Mature",
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries :: Application Frameworks']
)
