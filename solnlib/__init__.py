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

'''
The Splunk Software Development Kit for Solutions.
'''

from solnlib import pattern
from solnlib import log
from solnlib import utils
from solnlib import net_utils
from solnlib import ip_math
from solnlib import codecs
from solnlib import orphan_process_monitor
from solnlib import acl
from solnlib import credentials
from solnlib import metadata
from solnlib import server_info
from solnlib import splunkenv
from solnlib import http_request

__all__ = ['pattern',
           'log',
           'utils',
           'net_utils',
           'ip_math',
           'codecs',
           'orphan_process_monitor',
           'acl',
           'credentials',
           'metadata',
           'server_info',
           'splunkenv',
           'http_request']

__version__ = '1.0.0'
