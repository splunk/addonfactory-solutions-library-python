#
# Copyright 2024 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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
import signal
import time
from unittest import mock

import pytest

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
    assert mock_sleep_time[0] == sum(2**i for i in range(retries))

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


@pytest.mark.parametrize(
    "url,expected_scheme,expected_host,expected_port",
    [
        (
            "https://localhost:8089",
            "https",
            "localhost",
            8089,
        ),
        (
            "https://localhost:8089/",
            "https",
            "localhost",
            8089,
        ),
        (
            "https://localhost:8089/servicesNS/",
            "https",
            "localhost",
            8089,
        ),
        (
            "http://localhost:8089",
            "http",
            "localhost",
            8089,
        ),
        (
            "http://localhost:8089/",
            "http",
            "localhost",
            8089,
        ),
        (
            "http://localhost:8089/servicesNS/",
            "http",
            "localhost",
            8089,
        ),
        (
            "https://[::1]:8089",
            "https",
            "::1",
            8089,
        ),
    ],
)
def test_extract_http_scheme_host_port_when_success(
    url, expected_scheme, expected_host, expected_port
):
    scheme, host, port = utils.extract_http_scheme_host_port(url)

    assert expected_scheme == scheme
    assert expected_host == host
    assert expected_port == port


def test_extract_http_scheme_host_port_when_invalid():
    invalid = "localhost:8089"
    with pytest.raises(ValueError):
        _, _, _ = utils.extract_http_scheme_host_port(invalid)


@mock.patch.dict(os.environ, {"SPLUNK_HOME": "/opt/splunk"}, clear=True)
def test_remove_http_proxy_env_vars_preserves_non_http_env_vars():
    utils.remove_http_proxy_env_vars()

    assert "/opt/splunk" == os.getenv("SPLUNK_HOME")


@mock.patch.dict(os.environ, {"HTTP_PROXY": "proxy:80"}, clear=True)
def test_remove_http_proxy_env_vars_removes_proxy_related_env_vars():
    utils.remove_http_proxy_env_vars()

    assert None is os.getenv("HTTP_PROXY")


@mock.patch.dict(
    os.environ,
    {
        "SPLUNK_HOME": "/opt/splunk",
        "HTTP_PROXY": "proxy",
        "https_proxy": "proxy",
    },
    clear=True,
)
def test_remove_http_proxy_env_vars():
    utils.remove_http_proxy_env_vars()

    assert None is os.getenv("HTTP_PROXY")
    assert None is os.getenv("https_proxy")
    assert "/opt/splunk" == os.getenv("SPLUNK_HOME")
