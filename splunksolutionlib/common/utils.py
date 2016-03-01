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
Common utilities.
'''

import os
import os.path as op
import datetime
import signal


def handle_tear_down_signals(callback):
    '''Register handler for SIGTERM/SIGINT/SIGBREAK signal.

    Catch SIGTERM/SIGINT/SIGBREAK signals, and invoke callback
    Note: this should be called in main thread since Python only catches
    signals in main thread

    :param callback: Callback for tear down signals
    '''

    signal.signal(signal.SIGTERM, callback)
    signal.signal(signal.SIGINT, callback)

    if os.name == 'nt':
        signal.signal(signal.SIGBREAK, callback)


def datetime_to_seconds(dt):
    '''Convert UTC datatime to seconds since epoch.

    :param dt: Date time
    :type dt: datatime
    :returns: Seconds since epoch
    :rtype: float
    '''

    epoch_time = datetime.datetime.utcfromtimestamp(0)
    return (dt - epoch_time).total_seconds()


def is_true(val):
    '''Decide if `val` is true.

    :param val: Value to check
    :returns: True or False
    :rtype: bool
    '''

    value = str(val).strip().upper()
    if value in ('1', 'TRUE', 'T', 'Y', 'YES'):
        return True
    return False


def is_false(val):
    '''Decide if `val` is false.

    :param val: Value to check
    :returns: True or False
    :rtype: bool
    '''

    value = str(val).strip().upper()
    if value in ('0', 'FALSE', 'F', 'N', 'NO', 'NONE', ''):
        return True
    return False


def remove_http_proxy_env_vars():
    '''Remove http_proxy/https_proxy Env.

    These environment variables impacts some 3rd party libs like httplib2
    '''

    for k in ('http_proxy', 'https_proxy'):
        if k in os.environ:
            del os.environ[k]
        elif k.upper() in os.environ:
            del os.environ[k.upper()]


def get_appname_from_path(absolute_path):
    '''Deduce appname from `absolute_path`

    For example: the appname for /splunk/etc/apps/Splunk_TA_test/bin/test.py
    will be Splunk_TA_test

    :param absolute_path: Absolute file system path, like
        os.path.abspath(__file__)
    :returns: App name if successful otherwise return None
    :rtype: str
    '''

    absolute_path = op.normpath(absolute_path)
    parts = absolute_path.split(os.path.sep)
    parts.reverse()
    for key in ('apps', 'slave-apps', 'master-apps'):
        try:
            idx = parts.index(key)
        except ValueError:
            pass
        else:
            try:
                if parts[idx + 1] == 'etc':
                    return parts[idx - 1]
            except IndexError:
                pass
    return None


def escape_json_control_chars(json_str):
    '''Escape josn control chars in `json_str`.

    :param json_str: Json string to escape
    :returns: Escaped string
    :rtype: string
    '''

    control_chars = ((r'\n', '\\\\n'),
                     (r'\r', '\\\\r'),
                     (r'\r\n', '\\\\r\\\\n'))
    for ch, replace in control_chars:
        json_str = json_str.replace(ch, replace)
    return json_str
