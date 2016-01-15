# Copyright (C) 2005-2016 Splunk Inc. All Rights Reserved.

"""
Common utilit functions
"""

import os
import os.path as op
import datetime
import signal


def handle_tear_down_signals(callback):
    """
    Catch SIGTERM/SIGINT/SIGBREAK signals, and invoke callback
    Note: this should be called in main thread since Python only catches
    signals in main thread
    :callback: callable
    """

    signal.signal(signal.SIGTERM, callback)
    signal.signal(signal.SIGINT, callback)

    if os.name == "nt":
        signal.signal(signal.SIGBREAK, callback)


def datetime_to_seconds(dt):
    """
    Convert UTC datatime dt to seconds since epoch
    :dt: datetime object
    """

    epoch_time = datetime.datetime.utcfromtimestamp(0)
    return (dt - epoch_time).total_seconds()


def is_true(val):
    """
    Decide if `val` is true
    """

    value = str(val).strip().upper()
    if value in ("1", "TRUE", "T", "Y", "YES"):
        return True
    return False


def is_false(val):
    """
    Decide if `val` is false
    """

    value = str(val).strip().upper()
    if value in ("0", "FALSE", "F", "N", "NO", "NONE", ""):
        return True
    return False


def remove_http_proxy_env_vars():
    """
    Remove http_proxy/https_proxy from environ variables.
    These environment variables impacts some 3rd party libs like httplib2
    """

    for k in ("http_proxy", "https_proxy"):
        if k in os.environ:
            del os.environ[k]
        elif k.upper() in os.environ:
            del os.environ[k.upper()]


def get_appname_from_path(absolute_path):
    """
    Deduce appname from `absolute_path`
    For example: the appname for /splunk/etc/apps/Splunk_TA_aws/bin/aws_s3.py
    will be Splunk_TA_aws
    :absolute_path: absolute file system path, like os.path.abspath(__file__)
    :return: appname if successful otherwise return None
    """

    absolute_path = op.normpath(absolute_path)
    parts = absolute_path.split(os.path.sep)
    parts.reverse()
    for key in ("apps", "slave-apps", "master-apps"):
        try:
            idx = parts.index(key)
        except ValueError:
            continue
        else:
            try:
                if parts[idx + 1] == "etc":
                    return parts[idx - 1]
            except IndexError:
                pass
            continue
    return None


def escape_json_control_chars(json_str):
    """
    :json_str: string
    :return: esapced string
    """

    control_chars = ((r"\n", "\\\\n"), (r"\r", "\\\\r"),
                     (r"\r\n", "\\\\r\\\\n"))
    for ch, replace in control_chars:
        json_str = json_str.replace(ch, replace)
    return json_str
