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

import os.path as op
from setuptools import setup, Command

import splunksolutionlib


def run_test_suite():
    try:
        import unittest2 as unittest
    except ImportError:
        import unittest
    tests_dir = op.sep.join([op.dirname(op.abspath(__file__)), 'tests'])
    suite = unittest.defaultTestLoader.discover(tests_dir)
    unittest.TextTestRunner(verbosity=2).run(suite)


def run_test_suite_with_junit_output():
    try:
        import unittest2 as unittest
    except ImportError:
        import unittest
    import xmlrunner
    tests_dir = op.sep.join([op.dirname(op.abspath(__file__)), 'tests'])
    suite = unittest.defaultTestLoader.discover(tests_dir)
    xmlrunner.XMLTestRunner(output='testjunit-reports').run(suite)


class TestCommand(Command):
    '''
    Command to run the whole test suite.
    '''
    description = 'Run test full test suite.'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        run_test_suite()


class JunitXmlTestCommand(Command):
    '''
    Command to run the whole test suite.
    '''
    description = 'Run test full test suite with JUnit-formatted output.'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        run_test_suite_with_junit_output()

setup(
    name='splunksolutionlib',

    description='The Splunk Software Development Kit for Splunk Solutions',

    version=splunksolutionlib.__version__,

    author='Splunk, Inc.',

    author_email='Shanghai-TA-dev@splunk.com',

    license='http://www.apache.org/licenses/LICENSE-2.0',

    url='https://git.splunk.com/scm/solnsc/lib-solutions-python.git',

    packages=['splunksolutionlib',
              'splunksolutionlib.common',
              'splunksolutionlib.platform'],

    install_requires=[],

    cmdclass={'test': TestCommand,
              'testjunit': JunitXmlTestCommand},

    classifiers=[
        'Programming Language :: Python',
        'Development Status :: 1 - Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries :: Application Frameworks']
)
