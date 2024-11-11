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

from solnlib import conf_manager
from solnlib.soln_exceptions import (
    InvalidHostnameError,
    InvalidPortError,
    ConfManagerException,
    ConfStanzaNotExistException,
)
import pytest


@mock.patch.object(conf_manager, "ConfManager")
def test_get_log_level_when_error_getting_conf(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    mock_conf_manager.get_conf.side_effect = ConfManagerException
    expected_log_level = "INFO"

    log_level = conf_manager.get_log_level(
        logger=mock.MagicMock(),
        session_key="session_key",
        app_name="app_name",
        conf_name="conf_name",
    )

    assert expected_log_level == log_level


@mock.patch.object(conf_manager, "ConfManager")
def test_get_log_level_with_custom_values(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    mock_conf_manager.get_conf.return_value = {"my_logger": {"my_field": "DEBUG"}}
    expected_log_level = "DEBUG"

    log_level = conf_manager.get_log_level(
        logger=mock.MagicMock(),
        session_key="session_key",
        app_name="app_name",
        conf_name="conf_name",
        log_stanza="my_logger",
        log_level_field="my_field",
    )

    assert log_level == expected_log_level


@mock.patch.object(conf_manager, "ConfManager")
def test_get_log_level_with_no_logging_stanza(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    mock_conf_manager.get_conf.return_value = mock.MagicMock()
    mock_conf_manager.get_conf.return_value.get.side_effect = (
        ConfStanzaNotExistException
    )
    logger = mock.MagicMock()
    expected_log_level = "INFO"

    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key="session_key",
        app_name="app_name",
        conf_name="conf_name",
        log_stanza="my_logger",
        log_level_field="my_field",
    )

    assert log_level == expected_log_level
    assert logger.error.call_count == 1


@mock.patch.object(conf_manager, "ConfManager")
def test_get_log_level_with_default_fields(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    mock_conf_manager.get_conf.return_value = {"logging": {"loglevel": "WARN"}}
    expected_log_level = "WARN"

    log_level = conf_manager.get_log_level(
        logger=mock.MagicMock(),
        session_key="session_key",
        app_name="app_name",
        conf_name="conf_name",
    )

    assert log_level == expected_log_level


@mock.patch.object(conf_manager, "ConfManager")
def test_get_proxy_dict_with_default_fields(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    mock_conf_manager.get_conf.return_value = {
        "proxy": {
            "proxy_enabled": "",
            "proxy_type": "http",
            "proxy_url": "",
            "proxy_port": "",
            "proxy_username": "",
            "proxy_password": "",
            "proxy_rdns": "",
        }
    }

    expected_proxy_dict = {
        "proxy_enabled": "",
        "proxy_type": "http",
        "proxy_url": "",
        "proxy_port": "",
        "proxy_username": "",
        "proxy_password": "",
        "proxy_rdns": "",
    }

    proxy_dict = conf_manager.get_proxy_dict(
        logger=mock.MagicMock(),
        session_key="session_key",
        app_name="app_name",
        conf_name="conf_name",
    )

    assert proxy_dict == expected_proxy_dict


@mock.patch.object(conf_manager, "ConfManager")
def test_get_proxy_dict_with_custom_stanza_name(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    # Mock configuration with a different stanza name, e.g., "custom_stanza"
    mock_conf_manager.get_conf.return_value = {
        "custom_stanza": {
            "proxy_enabled": "",
            "proxy_type": "http",
            "proxy_url": "",
            "proxy_port": "",
            "proxy_username": "",
            "proxy_password": "",
            "proxy_rdns": "",
        }
    }

    expected_proxy_dict = {
        "proxy_enabled": "",
        "proxy_type": "http",
        "proxy_url": "",
        "proxy_port": "",
        "proxy_username": "",
        "proxy_password": "",
        "proxy_rdns": "",
    }

    proxy_dict = conf_manager.get_proxy_dict(
        logger=mock.MagicMock(),
        session_key="session_key",
        app_name="app_name",
        conf_name="conf_name",
        proxy_stanza="custom_stanza",  # passed different stanza name
    )

    assert proxy_dict == expected_proxy_dict


@mock.patch.object(conf_manager, "ConfManager")
def test_get_proxy_dict_invalid_port(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    # Mock return value for the "proxy" stanza
    mock_conf_manager.get_conf.return_value = {
        "proxy": {
            "proxy_enabled": "",
            "proxy_type": "http",
            "proxy_url": "example.com",
            "proxy_port": "invalid_port",  # Invalid port
            "proxy_username": "",
            "proxy_password": "",
            "proxy_rdns": "",
        }
    }

    with pytest.raises(InvalidPortError, match="The provided port is not valid."):
        conf_manager.get_proxy_dict(
            logger=mock.MagicMock(),
            session_key="session_key",
            app_name="app_name",
            conf_name="conf_name",
            proxy_port="proxy_port",  # Check for invalid port
        )


@mock.patch.object(conf_manager, "ConfManager")
def test_get_proxy_dict_invalid_hostname(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    # Mock return value for the "proxy" stanza
    mock_conf_manager.get_conf.return_value = {
        "proxy": {
            "proxy_enabled": "",
            "proxy_type": "http",
            "proxy_url": "invalid_host",  # Invalid hostname
            "proxy_port": "8080",
            "proxy_username": "",
            "proxy_password": "",
            "proxy_rdns": "",
        }
    }

    with pytest.raises(
        InvalidHostnameError, match="The provided hostname is not valid."
    ):
        conf_manager.get_proxy_dict(
            logger=mock.MagicMock(),
            session_key="session_key",
            app_name="app_name",
            conf_name="conf_name",
            proxy_host="proxy_url",  # Check for invalid hostname
        )


@mock.patch.object(conf_manager, "ConfManager")
def test_get_proxy_dict_conf_manager_exception(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    mock_conf_manager.get_conf.side_effect = ConfManagerException

    logger = mock.MagicMock()
    proxy_dict = conf_manager.get_proxy_dict(
        logger=logger,
        session_key="session_key",
        app_name="app_name",
        conf_name="conf_name",
    )

    logger.error.assert_called_once_with(
        "Failed to fetch configuration file 'conf_name'."
    )
    assert proxy_dict == {}
