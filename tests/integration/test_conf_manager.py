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

import context
import conftest
import pytest
from solnlib import conf_manager, soln_exceptions
from unittest import mock


VALID_PROXY_DICT = {
    "proxy_enabled": None,
    "proxy_type": "http",
    "proxy_url": "remote_host",
    "proxy_port": "3128",
    "proxy_username": None,
    "proxy_password": None,
    "proxy_rdns": None,
}


# conftest.py or test file

import tempfile
import shutil
import re
import importlib.util
import sys
import os
import pytest


@pytest.fixture
def patch_splunk_cli_common_module():
    import splunk.clilib.cli_common as comm

    original_path = comm.__file__

    with open(original_path, "r") as f:
        source = f.read()

    pattern = r'procArgs\s*=\s*\[\s*os\.path\.join\(\s*os\.environ\[\s*["\']SPLUNK_HOME["\']\s*\],\s*["\']bin["\'],\s*["\']splunkd["\']\s*\)\s*,\s*["\']local-rest-uri["\']\s*,\s*["\']-p["\']\s*,\s*mgmtPort\s*\]'
    replacement = 'procArgs = [os.path.join(os.environ["SPLUNK_HOME"], "bin", "splunk"), "cmd", "splunkd", "local-rest-uri", "-p", mgmtPort]'

    new_content = re.sub(pattern, replacement, source)

    temp_dir = tempfile.mkdtemp()
    patched_module_path = os.path.join(temp_dir, "module.py")

    with open(patched_module_path, "w") as f:
        f.write(new_content)

    spec = importlib.util.spec_from_file_location("splunk.clilib.cli_common", patched_module_path)
    patched_module = importlib.util.module_from_spec(spec)
    sys.modules["splunk.clilib.cli_common"] = patched_module
    spec.loader.exec_module(patched_module)

    yield

    shutil.rmtree(temp_dir)
    importlib.invalidate_caches()
    sys.modules.pop("splunk.clilib.cli_common", None)



def _build_conf_manager(session_key: str) -> conf_manager.ConfManager:
    return conf_manager.ConfManager(
        session_key,
        context.app,
        owner=context.owner,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )


def test_conf_manager_when_no_conf_then_throw_exception():
    session_key = context.get_session_key()
    cfm = _build_conf_manager(session_key)

    with pytest.raises(soln_exceptions.ConfManagerException):
        cfm.get_conf("non_existent_configuration_file")


def test_conf_manager_when_conf_file_exists_but_no_specific_stanza_then_throw_exception():
    session_key = context.get_session_key()
    cfm = _build_conf_manager(session_key)

    splunk_ta_addon_settings_conf_file = cfm.get_conf("splunk_ta_addon_settings")

    with pytest.raises(soln_exceptions.ConfStanzaNotExistException):
        splunk_ta_addon_settings_conf_file.get(
            "non_existent_stanza_under_existing_conf_file"
        )


@pytest.mark.parametrize(
    "stanza_name,expected_result",
    [
        ("logging", True),
        ("proxy", True),
        ("non_existent_stanza_under_existing_conf_file", False),
    ],
)
def test_conf_manager_stanza_exist(stanza_name, expected_result):
    session_key = context.get_session_key()
    cfm = _build_conf_manager(session_key)

    splunk_ta_addon_settings_conf_file = cfm.get_conf("splunk_ta_addon_settings")

    assert (
        splunk_ta_addon_settings_conf_file.stanza_exist(stanza_name) == expected_result
    )


def test_conf_manager_when_conf_file_exists():
    session_key = context.get_session_key()
    cfm = _build_conf_manager(session_key)

    splunk_ta_addon_settings_conf_file = cfm.get_conf("splunk_ta_addon_settings")

    expected_result = {
        "disabled": "0",
        "eai:access": {
            "app": "solnlib_demo",
            "can_change_perms": "1",
            "can_list": "1",
            "can_share_app": "1",
            "can_share_global": "1",
            "can_share_user": "0",
            "can_write": "1",
            "modifiable": "1",
            "owner": "nobody",
            "perms": {"read": ["*"], "write": ["admin"]},
            "removable": "0",
            "sharing": "global",
        },
        "eai:appName": "solnlib_demo",
        "eai:userName": "nobody",
        "log_level": "DEBUG",
    }
    assert splunk_ta_addon_settings_conf_file.get("logging") == expected_result


def test_conf_manager_delete_non_existent_stanza_then_throw_exception():
    session_key = context.get_session_key()
    cfm = _build_conf_manager(session_key)

    splunk_ta_addon_settings_conf_file = cfm.get_conf("splunk_ta_addon_settings")

    with pytest.raises(soln_exceptions.ConfStanzaNotExistException):
        splunk_ta_addon_settings_conf_file.delete(
            "non_existent_stanza_under_existing_conf_file"
        )


def test_conf_manager_create_conf():
    session_key = context.get_session_key()
    cfm = _build_conf_manager(session_key)

    conf_file = cfm.create_conf("conf_file_that_did_not_exist_before")
    conf_file.update("stanza", {"key": "value"})

    assert conf_file.get("stanza")["key"] == "value"


def test_conf_manager_update_conf_with_encrypted_keys():
    session_key = context.get_session_key()
    cfm = _build_conf_manager(session_key)

    conf_file = cfm.create_conf("conf_file_with_encrypted_keys")
    conf_file.update(
        "stanza", {"key1": "value1", "key2": "value2"}, encrypt_keys=["key2"]
    )

    assert conf_file.get("stanza")["key2"] == "value2"


def test_get_log_level(patch_splunk_cli_common_module, monkeypatch):

    conftest.mock_splunk(monkeypatch)

    session_key = context.get_session_key()
    expected_log_level = "DEBUG"

    log_level = conf_manager.get_log_level(
        logger=mock.MagicMock(),
        session_key=session_key,
        app_name="solnlib_demo",
        conf_name="splunk_ta_addon_settings",
        log_level_field="log_level",
    )

    assert expected_log_level == log_level


def test_get_log_level_incorrect_log_level_field(monkeypatch):
    conftest.mock_splunk(monkeypatch)

    session_key = context.get_session_key()
    expected_log_level = "INFO"

    log_level = conf_manager.get_log_level(
        logger=mock.MagicMock(),
        session_key=session_key,
        app_name="solnlib_demo",
        conf_name="splunk_ta_addon_settings",
    )

    assert expected_log_level == log_level


def test_get_proxy_dict(monkeypatch):
    conftest.mock_splunk(monkeypatch)

    session_key = context.get_session_key()
    expected_proxy_dict = VALID_PROXY_DICT
    proxy_dict = conf_manager.get_proxy_dict(
        logger=mock.MagicMock(),
        session_key=session_key,
        app_name="solnlib_demo",
        conf_name="splunk_ta_addon_settings",
    )
    assert expected_proxy_dict == proxy_dict


def test_invalid_proxy_port(monkeypatch):
    conftest.mock_splunk(monkeypatch)

    session_key = context.get_session_key()

    with pytest.raises(soln_exceptions.InvalidPortError):
        conf_manager.get_proxy_dict(
            logger=mock.MagicMock(),
            session_key=session_key,
            app_name="solnlib_demo",
            conf_name="splunk_ta_addon_settings_invalid",
            proxy_stanza="invalid_proxy",
            proxy_port="proxy_port",
        )


def test_invalid_proxy_host(monkeypatch):
    conftest.mock_splunk(monkeypatch)

    session_key = context.get_session_key()

    with pytest.raises(soln_exceptions.InvalidHostnameError):
        conf_manager.get_proxy_dict(
            logger=mock.MagicMock(),
            session_key=session_key,
            app_name="solnlib_demo",
            conf_name="splunk_ta_addon_settings_invalid",
            proxy_stanza="invalid_proxy",
            proxy_host="proxy_url",
        )


def test_conf_manager_exception():
    session_key = context.get_session_key()

    with pytest.raises(soln_exceptions.ConfManagerException):
        conf_manager.get_proxy_dict(
            logger=mock.MagicMock(),
            session_key=session_key,
            app_name="solnlib_demo",
            conf_name="splunk_ta_addon_settings_not_valid",
        )


def test_conf_stanza_not_exist_exception(monkeypatch):
    conftest.mock_splunk(monkeypatch)

    session_key = context.get_session_key()

    with pytest.raises(soln_exceptions.ConfStanzaNotExistException):
        conf_manager.get_proxy_dict(
            logger=mock.MagicMock(),
            session_key=session_key,
            app_name="solnlib_demo",
            conf_name="splunk_ta_addon_settings",
            proxy_stanza="invalid_proxy",
        )
