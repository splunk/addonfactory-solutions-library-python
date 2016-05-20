# Copyright 2016 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

'''
The Splunk Software Development Kit for Solutions.
'''

from solnlib import acl
from solnlib import compression
from solnlib import credentials
from solnlib import user_access
from solnlib import ip_math
from solnlib import log
from solnlib import metadata
from solnlib import net_utils
from solnlib import file_monitor
from solnlib import orphan_process_monitor
from solnlib import pattern
from solnlib import server_info
from solnlib import splunk_rest_client
from solnlib import splunkenv
from solnlib import utils

__all__ = ['acl',
           'compression',
           'credentials',
           'user_access',
           'ip_math',
           'log',
           'metadata',
           'net_utils',
           'file_monitor',
           'orphan_process_monitor',
           'pattern',
           'server_info',
           'splunk_rest_client',
           'splunkenv',
           'utils']

__version__ = '1.1.0'
