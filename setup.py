try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import sys

VERSION = '0.1.0'

setup(name='splunksolutionlib',
        version=VERSION,
        author='Splunk, Inc.',
        author_email='Shanghai-TA-dev@splunk.com',
        url='https://git.splunk.com/scm/solnsc/lib-solutions-python.git',
        description='The Splunk Software Development Kit for Solutions',
        packages=['splunksolutionlib', 'splunksolutionlib.common', 'splunksolutionlib.platform'],

        classifiers = [
            "Programming Language :: Python",
            "Development Status :: 1 - Alpha",
            "Environment :: Other Environment",
            "Intended Audience :: Developers",
            "Operating System :: OS Independent",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Software Development :: Libraries :: Application Frameworks",
        ],
)
