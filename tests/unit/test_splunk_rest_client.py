#
# Copyright 2023 Splunk Inc.
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
import os
from unittest import mock

import pytest
from solnlib.splunk_rest_client import MAX_REQUEST_RETRIES

from requests.exceptions import ConnectionError
from solnlib import splunk_rest_client
from solnlib.splunk_rest_client import SplunkRestClient


@mock.patch.dict(os.environ, {"SPLUNK_HOME": "/opt/splunk"}, clear=True)
@mock.patch("solnlib.splunk_rest_client.get_splunkd_access_info")
def test_init_with_only_required_fields_when_splunk_env(mock_get_splunkd_access_info):
    mock_get_splunkd_access_info.return_value = "https", "localhost", 8089
    splunk_rest_client.SplunkRestClient(
        "session_key",
        "app",
        "owner",
    )


@mock.patch.dict(os.environ, {"SPLUNK_HOME": "/opt/splunk"}, clear=True)
@mock.patch("solnlib.splunk_rest_client.get_splunkd_access_info")
def test_init_with_only_host_when_splunk_env(mock_get_splunkd_access_info):
    mock_get_splunkd_access_info.return_value = "https", "localhost", 8089
    splunk_rest_client.SplunkRestClient("session_key", "app", "owner", host="localhost")


def test_init_with_only_required_fields_when_not_in_splunk_env():
    with pytest.raises(ValueError):
        splunk_rest_client.SplunkRestClient(
            "session_key",
            "app",
            "owner",
        )


def test_init_with_only_host_and_port():
    with pytest.raises(ValueError):
        splunk_rest_client.SplunkRestClient(
            "session_key",
            "app",
            "nobody",
            host="localhost",
            port=8089,
        )


def test_init_with_all_fields():
    splunk_rest_client.SplunkRestClient(
        "session_key",
        "app",
        "nobody",
        scheme="https",
        host="localhost",
        port=8089,
    )


def test_init_with_invalid_port():
    with pytest.raises(ValueError):
        splunk_rest_client.SplunkRestClient(
            "session_key",
            "app",
            "nobody",
            scheme="https",
            host="localhost",
            port=99999,
        )


@mock.patch.dict(os.environ, {"SPLUNK_HOME": "/opt/splunk"}, clear=True)
@mock.patch("http.client.HTTPResponse")
@mock.patch("urllib3.HTTPConnectionPool._make_request")
def test_no_retry_error(http_conn_pool, http_resp, monkeypatch):
    session_key = "123"
    context = {"pool_connections": 5}
    rest_client = SplunkRestClient("msg_name_1", session_key, "_", **context)

    mock_resp = http_resp()
    mock_resp.status = 200
    mock_resp.reason = "TEST OK"

    side_effects = [ConnectionError(), ConnectionError(), ConnectionError(), mock_resp]
    http_conn_pool.side_effect = side_effects
    res = rest_client.get("test")
    assert http_conn_pool.call_count == len(side_effects)
    assert res.reason == mock_resp.reason

    side_effects = [ConnectionError()] * (MAX_REQUEST_RETRIES + 1) + [mock_resp]
    http_conn_pool.side_effect = side_effects
    with pytest.raises(ConnectionError):
        rest_client.get("test")
