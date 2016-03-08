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
import re
import datetime
import signal
import socket


def handle_tear_down_signals(callback):
    '''Register handler for SIGTERM/SIGINT/SIGBREAK signal.

    Catch SIGTERM/SIGINT/SIGBREAK signals, and invoke callback
    Note: this should be called in main thread since Python only catches
    signals in main thread.

    :param callback: Callback for tear down signals.
    '''

    signal.signal(signal.SIGTERM, callback)
    signal.signal(signal.SIGINT, callback)

    if os.name == 'nt':
        signal.signal(signal.SIGBREAK, callback)


def datetime_to_seconds(dt):
    '''Convert UTC datatime to seconds since epoch.

    :param dt: Date time.
    :type dt: datatime.
    :returns: Seconds since epoch.
    :rtype: ``float``
    '''

    epoch_time = datetime.datetime.utcfromtimestamp(0)
    return (dt - epoch_time).total_seconds()


def is_true(val):
    '''Decide if `val` is true.

    :param val: Value to check.
    :returns: True or False.
    :rtype: ``bool``
    '''

    value = str(val).strip().upper()
    if value in ('1', 'TRUE', 'T', 'Y', 'YES'):
        return True
    return False


def is_false(val):
    '''Decide if `val` is false.

    :param val: Value to check.
    :returns: True or False.
    :rtype: ``bool``
    '''

    value = str(val).strip().upper()
    if value in ('0', 'FALSE', 'F', 'N', 'NO', 'NONE', ''):
        return True
    return False


def escape_json_control_chars(json_str):
    '''Escape json control chars in `json_str`.

    :param json_str: Json string to escape.
    :returns: Escaped string.
    :rtype: ``string``
    '''

    control_chars = ((r'\n', '\\\\n'),
                     (r'\r', '\\\\r'),
                     (r'\r\n', '\\\\r\\\\n'))
    for ch, replace in control_chars:
        json_str = json_str.replace(ch, replace)
    return json_str


def is_valid_ip(addr):
    """Validate an IP address.

    :param value: IP address to validate.
    :returns: True if is valid else False.
    :rtype: ``bool``
    """

    ip_rx = re.compile(r'''
        ^(((
              [0-1]\d{2}                  # matches 000-199
            | 2[0-4]\d                    # matches 200-249
            | 25[0-5]                     # matches 250-255
            | \d{1,2}                     # matches 0-9, 00-99
        )\.){3})                          # 3 of the preceding stanzas
        ([0-1]\d{2}|2[0-4]\d|25[0-5]|\d{1,2})$     # final octet
    ''', re.VERBOSE)

    try:
        return bool(ip_rx.match(addr.strip()))
    except AttributeError:
        # Value was not a string
        return False


def resolve_hostname(addr):
    """Try to resolve an IP to a host name and returns None
    on common failures.

    :param addr: IP address to resolve.
    :returns: host name if success else None.
    :rtype: ``string``

    :raises ValueError: If `addr` is not a valid address
    """

    if is_valid_ip(addr):
        try:
            name, _, _ = socket.gethostbyaddr(addr)
            return name
        except socket.gaierror:
            # [Errno 8] nodename nor servname provided, or not known
            pass
        except socket.herror:
            # [Errno 1] Unknown host
            pass
        except socket.timeout:
            # Timeout.
            pass

        return None
    else:
        raise ValueError('Invalid ip address.')
