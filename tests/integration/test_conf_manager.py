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
import os.path as op
import sys
import pytest
from solnlib import conf_manager
from unittest import mock


sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))


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

    with pytest.raises(conf_manager.ConfManagerException):
        cfm.get_conf("non_existent_configuration_file")


def test_conf_manager_when_conf_file_exists_but_no_specific_stanza_then_throw_exception():
    session_key = context.get_session_key()
    cfm = _build_conf_manager(session_key)

    splunk_ta_addon_settings_conf_file = cfm.get_conf("splunk_ta_addon_settings")

    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        splunk_ta_addon_settings_conf_file.get(
            "non_existent_stanza_under_existing_conf_file"
        )


@pytest.mark.parametrize(
    "stanza_name,expected_result",
    [
        ("logging", True),
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

    with pytest.raises(conf_manager.ConfStanzaNotExistException):
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


def test_get_log_level():
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


def test_get_log_level_incorrect_log_level_field():
    session_key = context.get_session_key()
    expected_log_level = "INFO"

    log_level = conf_manager.get_log_level(
        logger=mock.MagicMock(),
        session_key=session_key,
        app_name="solnlib_demo",
        conf_name="splunk_ta_addon_settings",
    )

    assert expected_log_level == log_level
