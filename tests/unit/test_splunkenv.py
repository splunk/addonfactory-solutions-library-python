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

from unittest import mock

import common
import pytest

from solnlib import splunkenv


def test_get_splunk_host_info(monkeypatch):
    common.mock_splunkhome(monkeypatch)
    common.mock_gethostname(monkeypatch)

    server_name, host_name = splunkenv.get_splunk_host_info(common.SESSION_KEY)
    assert server_name == "unittestServer"
    assert host_name == "unittestServer"


@mock.patch.object(splunkenv, "get_conf_key_value")
@pytest.mark.parametrize(
    "enable_splunkd_ssl,mgmt_host_port,expected_scheme,expected_host,expected_port",
    [
        (
            "true",
            "127.0.0.1:8089",
            "https",
            "127.0.0.1",
            8089,
        ),
        (
            "true",
            "localhost:8089",
            "https",
            "localhost",
            8089,
        ),
        (
            "false",
            "127.0.0.1:8089",
            "http",
            "127.0.0.1",
            8089,
        ),
        (
            "false",
            "localhost:8089",
            "http",
            "localhost",
            8089,
        ),
        (
            "false",
            "1.2.3.4:5678",
            "http",
            "1.2.3.4",
            5678,
        ),
        (
            "true",
            "[::1]:8089",
            "https",
            "[::1]",
            8089,
        ),
        (
            "false",
            "[::1]:8089",
            "http",
            "[::1]",
            8089,
        ),
    ],
)
def test_get_splunkd_access_info(
    mock_get_conf_key_value,
    enable_splunkd_ssl,
    mgmt_host_port,
    expected_scheme,
    expected_host,
    expected_port,
):
    mock_get_conf_key_value.side_effect = [
        enable_splunkd_ssl,
        mgmt_host_port,
    ]

    scheme, host, port = splunkenv.get_splunkd_access_info()

    assert expected_scheme == scheme
    assert expected_host == host
    assert expected_port == port


def test_splunkd_uri(monkeypatch):
    common.mock_splunkhome(monkeypatch)

    uri = splunkenv.get_splunkd_uri(common.SESSION_KEY)
    assert uri == "https://127.0.0.1:8089"

    monkeypatch.setenv("SPLUNK_BINDIP", "10.0.0.2:7080")
    uri = splunkenv.get_splunkd_uri(common.SESSION_KEY)
    assert uri == "https://10.0.0.2:8089"

    monkeypatch.setenv("SPLUNK_BINDIP", "10.0.0.3")
    uri = splunkenv.get_splunkd_uri(common.SESSION_KEY)
    assert uri == "https://10.0.0.3:8089"

    monkeypatch.setenv("SPLUNKD_URI", "https://10.0.0.1:8089")
    uri = splunkenv.get_splunkd_uri(common.SESSION_KEY)
    assert uri == "https://10.0.0.1:8089"
