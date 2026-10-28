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

    server_name, host_name = splunkenv.get_splunk_host_info("session_key")
    assert server_name == "unittestServer"
    assert host_name == "unittestServer"


@mock.patch("solnlib.splunkenv.use_btool")
def test_get_splunk_host_info_backdoor(mock_flag, monkeypatch):
    mock_flag.return_value = True
    common.mock_splunkhome(monkeypatch)
    common.mock_gethostname(monkeypatch)

    server_name, host_name = splunkenv.get_splunk_host_info("session_key")
    assert server_name == "unittestServerBtool"
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

    uri = splunkenv.get_splunkd_uri("session_key")
    assert uri == "https://127.0.0.1:8089"

    monkeypatch.setenv("SPLUNK_BINDIP", "10.0.0.2:7080")
    uri = splunkenv.get_splunkd_uri("session_key")
    assert uri == "https://10.0.0.2:8089"

    monkeypatch.setenv("SPLUNK_BINDIP", "10.0.0.3")
    uri = splunkenv.get_splunkd_uri("session_key")
    assert uri == "https://10.0.0.3:8089"

    monkeypatch.setenv("SPLUNKD_URI", "https://10.0.0.1:8089")
    uri = splunkenv.get_splunkd_uri("session_key")
    assert uri == "https://10.0.0.1:8089"


@mock.patch("solnlib.splunkenv.use_btool")
def test_splunkd_uri_backdoor(mock_flag, monkeypatch):
    mock_flag.return_value = True

    common.mock_splunkhome(monkeypatch)

    uri = splunkenv.get_splunkd_uri("session_key")
    assert uri == "http://127.0.0.2:8079"

    monkeypatch.setenv("SPLUNK_BINDIP", "10.0.0.2:7080")
    uri = splunkenv.get_splunkd_uri("session_key")
    assert uri == "http://10.0.0.2:8079"

    monkeypatch.setenv("SPLUNK_BINDIP", "10.0.0.3")
    uri = splunkenv.get_splunkd_uri("session_key")
    assert uri == "http://10.0.0.3:8079"

    monkeypatch.setenv("SPLUNKD_URI", "https://10.0.0.1:8089")
    uri = splunkenv.get_splunkd_uri("session_key")
    assert uri == "https://10.0.0.1:8089"


def test_splunkenv_used_outside_splunk_env():
    with pytest.raises(ImportError) as exc_info:
        splunkenv._get_conf_stanzas_from_splunk_api(
            "server", "app", session_key="session_key"
        )
    assert exc_info.value.args[0] == "This module requires Splunk to be installed."


@pytest.mark.parametrize(
    "rel_path,expected",
    [
        ("etc/apps/Splunk_TA_aws/lib/solnlib/splunkenv.py", "Splunk_TA_aws"),
        ("etc/apps/Splunk_TA_aws/bin/lib/solnlib/splunkenv.py", "Splunk_TA_aws"),
        ("etc/peer-apps/Splunk_TA_aws/lib/solnlib/splunkenv.py", "Splunk_TA_aws"),
        ("etc/slave-apps/Splunk_TA_aws/lib/solnlib/splunkenv.py", "Splunk_TA_aws"),
        ("etc/apps/Splunk_TA_aws", "Splunk_TA_aws"),
        ("etc/apps", None),
        ("src/apps/Splunk_TA_aws/lib/solnlib/splunkenv.py", None),
        ("etc/apps/Splunk_TA_aws/lib/pkg/etc/apps/inner/x.py", "Splunk_TA_aws"),
        ("etc/deployment-apps/Splunk_TA_aws/bin/input.py", None),
        ("etc/shcluster/apps/Splunk_TA_aws/bin/input.py", None),
        ("checkout/solnlib/splunkenv.py", None),
    ],
)
def test_get_app_name_from_path(tmp_path, monkeypatch, rel_path, expected):
    monkeypatch.delenv("SPLUNK_ETC", raising=False)
    assert splunkenv._get_app_name_from_path(str(tmp_path / rel_path)) == expected


def test_get_app_name_from_path_relocated_splunk_etc(tmp_path, monkeypatch):
    splunk_etc = tmp_path / "splunkcfg"
    script = splunk_etc / "apps" / "Splunk_TA_aws" / "bin" / "input.py"
    monkeypatch.setenv("SPLUNK_ETC", str(splunk_etc))
    assert splunkenv._get_app_name_from_path(str(script)) == "Splunk_TA_aws"
    monkeypatch.delenv("SPLUNK_ETC")
    assert splunkenv._get_app_name_from_path(str(script)) is None


def test_get_app_name_from_path_keeps_symlinked_app_name(tmp_path):
    target = tmp_path / "src" / "MyTA"
    (target / "bin").mkdir(parents=True)
    (tmp_path / "etc" / "apps").mkdir(parents=True)
    (tmp_path / "etc" / "apps" / "MyTA").symlink_to(target)
    script = tmp_path / "etc" / "apps" / "MyTA" / "bin" / "input.py"
    assert splunkenv._get_app_name_from_path(str(script)) == "MyTA"


def test_get_running_app_name_prefers_main_script(tmp_path, monkeypatch):
    monkeypatch.setattr(
        splunkenv.__main__,
        "__file__",
        str(tmp_path / "etc/apps/TA_running/bin/input.py"),
        raising=False,
    )
    monkeypatch.setattr(
        splunkenv, "__file__", str(tmp_path / "etc/apps/TA_lib/lib/solnlib/x.py")
    )
    assert splunkenv._get_running_app_name() == "TA_running"


def test_get_running_app_name_uses_argv_without_main_file(tmp_path, monkeypatch):
    monkeypatch.delattr(splunkenv.__main__, "__file__", raising=False)
    monkeypatch.setattr(
        splunkenv.sys, "argv", [str(tmp_path / "etc/apps/TA_argv/bin/input.py")]
    )
    assert splunkenv._get_running_app_name() == "TA_argv"


def test_get_running_app_name_without_sys_argv(tmp_path, monkeypatch):
    monkeypatch.delattr(splunkenv.__main__, "__file__", raising=False)
    monkeypatch.delattr(splunkenv.sys, "argv")
    monkeypatch.setattr(
        splunkenv, "__file__", str(tmp_path / "etc/apps/TA_lib/lib/solnlib/x.py")
    )
    assert splunkenv._get_running_app_name() == "TA_lib"


def test_get_running_app_name_survives_path_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(
        splunkenv.__main__, "__file__", "relative/input.py", raising=False
    )
    monkeypatch.setattr(splunkenv.op, "abspath", mock.Mock(side_effect=OSError))
    assert splunkenv._get_running_app_name() is None


def test_get_running_app_name_falls_back_to_solnlib_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        splunkenv.__main__,
        "__file__",
        str(tmp_path / "opt/splunk/lib/python3/splunk/persistconn/appserver.py"),
        raising=False,
    )
    monkeypatch.setattr(
        splunkenv, "__file__", str(tmp_path / "etc/apps/TA_lib/lib/solnlib/x.py")
    )
    assert splunkenv._get_running_app_name() == "TA_lib"


def test_get_running_app_name_none_outside_splunk(tmp_path, monkeypatch):
    monkeypatch.setattr(
        splunkenv.__main__, "__file__", str(tmp_path / "x.py"), raising=False
    )
    monkeypatch.setattr(splunkenv, "__file__", str(tmp_path / "solnlib/x.py"))
    assert splunkenv._get_running_app_name() is None
