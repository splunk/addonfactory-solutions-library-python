#
# Copyright 2021 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import datetime
import logging
import os
import os.path as op
import signal
import sys
import time

import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import utils


def test_handle_teardown_signals(monkeypatch):
    test_handle_teardown_signals.should_teardown = False

    def sig_handler(signum, frame):
        test_handle_teardown_signals.should_teardown = True

    utils.handle_teardown_signals(sig_handler)
    os.kill(os.getpid(), signal.SIGINT)
    assert test_handle_teardown_signals.should_teardown


def test_datatime_to_seconds(monkeypatch):
    total_seconds = 1456755646.0
    dt = datetime.datetime(2016, 2, 29, 14, 20, 46, 0)
    assert total_seconds == utils.datetime_to_seconds(dt)


def test_is_false(monkeypatch):
    for val in ("0", "FALSE", "F", "N", "NO", "NONE", "", None):
        assert utils.is_false(val)

    for val in ("1", "TRUE", "T", "Y", "YES"):
        assert not utils.is_false(val)

    for val in ("00", "FF", "NN", "NONO", "434324"):
        assert not utils.is_false(val)


def test_is_true(monkeypatch):
    for val in ("1", "TRUE", "T", "Y", "YES"):
        assert utils.is_true(val)

    for val in ("0", "FALSE", "F", "N", "NO", "NONE", "", None):
        assert not utils.is_true(val)

    for val in ("00", "FF", "NN", "NONO", "434324"):
        assert not utils.is_true(val)


def test_escape_json_control_chars(monkeypatch):
    str1 = r"hello\nworld"
    escaped_str1 = r"hello\\nworld"
    assert escaped_str1 == utils.escape_json_control_chars(str1)

    str1 = r"hello\rworld"
    escaped_str1 = r"hello\\rworld"
    assert escaped_str1 == utils.escape_json_control_chars(str1)

    str1 = r"hello\r\nworld"
    escaped_str1 = r"hello\\r\\nworld"
    assert escaped_str1 == utils.escape_json_control_chars(str1)


def test_retry(monkeypatch):
    def _old_func():
        raise ValueError("Exception for test.")

    _new_func = utils.retry(retries=1)(_old_func)
    with pytest.raises(ValueError):
        _new_func()
    _new_func = utils.retry(retries=1, exceptions=[TypeError])(_old_func)
    with pytest.raises(ValueError):
        _new_func()

    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, "sleep", mock_sleep)

    retries = 3
    tried = [0]

    @utils.retry(retries=retries, reraise=False)
    def mock_func():
        tried[0] += 1
        raise ValueError()

    mock_func()
    assert tried[0] == retries + 1
    assert mock_sleep_time[0] == sum(2 ** i for i in range(retries))

    record = [0, 0]

    def mock_warning(msg, *args, **kwargs):
        record[0] += 1

    def mock_error(msg, *args, **kwargs):
        record[1] += 1

    monkeypatch.setattr(logging, "warning", mock_warning)
    monkeypatch.setattr(logging, "error", mock_error)
    mock_func()

    assert record[0] == 4
    assert record[1] == 0


def test_extract_http_scheme_host_port(monkeypatch):
    h1 = "https://localhost:8089"
    scheme, host, port = utils.extract_http_scheme_host_port(h1)
    assert scheme == "https" and host == "localhost" and port == 8089

    h2 = "https://localhost:8089/"
    scheme, host, port = utils.extract_http_scheme_host_port(h2)
    assert scheme == "https" and host == "localhost" and port == 8089

    h3 = "https://localhost:8089/servicesNS/"
    scheme, host, port = utils.extract_http_scheme_host_port(h3)
    assert scheme == "https" and host == "localhost" and port == 8089

    h1 = "http://localhost:8089"
    scheme, host, port = utils.extract_http_scheme_host_port(h1)
    assert scheme == "http" and host == "localhost" and port == 8089

    h2 = "http://localhost:8089/"
    scheme, host, port = utils.extract_http_scheme_host_port(h2)
    assert scheme == "http" and host == "localhost" and port == 8089

    h3 = "http://localhost:8089/servicesNS/"
    scheme, host, port = utils.extract_http_scheme_host_port(h3)
    assert scheme == "http" and host == "localhost" and port == 8089

    invalid = "localhost:8089"
    try:
        scheme, host, port = utils.extract_http_scheme_host_port(invalid)
    except ValueError:
        pass
    else:
        assert 0

    invalid = None
    try:
        scheme, host, port = utils.extract_http_scheme_host_port(invalid)
    except Exception:
        pass
    else:
        assert 0
