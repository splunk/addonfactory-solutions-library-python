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

import os
import os.path as op
import sys

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import splunkenv


def test_splunkhome_path(monkeypatch):
    common.mock_splunkhome(monkeypatch)

    splunkhome_path = splunkenv.make_splunkhome_path(["etc", "apps"])
    assert splunkhome_path == os.environ["SPLUNK_HOME"] + "etc/apps"


def test_get_splunk_host_info(monkeypatch):
    common.mock_splunkhome(monkeypatch)
    common.mock_gethostname(monkeypatch)

    server_name, host_name = splunkenv.get_splunk_host_info()
    assert server_name == "unittestServer"
    assert host_name == "unittestServer"


def test_splunk_bin(monkeypatch):
    common.mock_splunkhome(monkeypatch)

    splunk_bin = splunkenv.get_splunk_bin()
    assert splunk_bin in (
        os.environ["SPLUNK_HOME"] + "bin/splunk",
        os.environ["SPLUNK_HOME"] + "bin/splunk.exe",
    )


def test_get_splunkd_access_info(monkeypatch):
    common.mock_splunkhome(monkeypatch)

    scheme, host, port = splunkenv.get_splunkd_access_info()
    assert scheme == "https"
    assert host == "127.0.0.1"
    assert port == 8089


def test_splunkd_uri(monkeypatch):
    common.mock_splunkhome(monkeypatch)

    uri = splunkenv.get_splunkd_uri()
    assert uri == "https://127.0.0.1:8089"

    monkeypatch.setenv("SPLUNK_BINDIP", "10.0.0.2:7080")
    uri = splunkenv.get_splunkd_uri()
    assert uri == "https://10.0.0.2:8089"

    monkeypatch.setenv("SPLUNK_BINDIP", "10.0.0.3")
    uri = splunkenv.get_splunkd_uri()
    assert uri == "https://10.0.0.3:8089"

    monkeypatch.setenv("SPLUNKD_URI", "https://10.0.0.1:8089")
    uri = splunkenv.get_splunkd_uri()
    assert uri == "https://10.0.0.1:8089"
