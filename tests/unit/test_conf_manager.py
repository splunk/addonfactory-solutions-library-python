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

import hashlib
from unittest import mock

import common
import pytest
from splunklib import binding, client
from splunklib.data import record

from solnlib import conf_manager


def test_conf_manager(monkeypatch):
    credentials_store = {}
    all_stanzas = {}

    def mock_storage_passwords_list(self, count=None, **kwargs):
        return credentials_store.values()

    def mock_storage_passwords_create(self, password, username, realm=None):
        title = f"{realm}:{username}:" if realm else f":{username}:"
        password = client.StoragePassword(
            None,
            f"storage/passwords/{title}",
            state=record(
                {
                    "content": {
                        "clear_password": password,
                        "encr_password": hashlib.md5(password.encode()).digest(),
                        "password": "********",
                        "realm": realm,
                        "username": username,
                    },
                    "title": title,
                }
            ),
        )
        credentials_store[title] = password
        return password

    def mock_storage_passwords_delete(self, username, realm=None):
        title = f"{realm}:{username}:" if realm else f":{username}:"
        if title in credentials_store:
            del credentials_store[title]
        else:
            raise KeyError("No such entity %s" % username)

    def mock_storage_password_delete(self):
        if self.name in credentials_store:
            del credentials_store[self.name]
        else:
            raise KeyError("No such entity %s" % self.name)

    def mock_configuration_get(
        self, name="", owner=None, app=None, sharing=None, **query
    ):
        return common.make_response_record("")

    def mock_configuration_file_list(self, count=None, **kwargs):
        if not hasattr(mock_configuration_file_list, "normal_mode"):
            mock_configuration_file_list.normal_mode = True
            raise binding.HTTPError(common.make_response_record("", status=404))
        else:
            if "name" in kwargs:
                if kwargs["name"] in all_stanzas:
                    stanza_mgr = client.Stanza(
                        self.service,
                        "configs/conf-test/{}/".format(kwargs["name"]),
                        skip_refresh=True,
                    )
                    stanza_mgr._state = common.record(
                        {
                            "title": kwargs["name"],
                            "access": common.record({"app": "test"}),
                            "content": all_stanzas[kwargs["name"]],
                        }
                    )
                    return [stanza_mgr]
                else:
                    raise binding.HTTPError(common.make_response_record("", status=404))
            else:
                stanza_mgrs = []
                for stanza_name, stanza in list(all_stanzas.items()):
                    stanza_mgr = client.Stanza(
                        self.service,
                        f"configs/conf-test/{stanza_name}/",
                        skip_refresh=True,
                    )
                    stanza_mgr._state = common.record(
                        {
                            "title": stanza_name,
                            "access": common.record({"app": "test"}),
                            "content": stanza,
                        }
                    )
                    stanza_mgrs.append(stanza_mgr)

                return stanza_mgrs

    def mock_configuration_file_get(
        self, name="", owner=None, app=None, sharing=None, **query
    ):
        return common.make_response_record("")

    def mock_configuration_file_create(self, name, **params):
        stanza_mgr = client.Stanza(
            self.service, f"configs/conf-test/{name}/", skip_refresh=True
        )
        stanza_mgr._state = common.record({"title": name, "content": {}})
        return stanza_mgr

    def mock_configuration_file_delete(self, name, **params):
        del all_stanzas[name]

    def mock_stanza_submit(self, stanza):
        all_stanzas[self.name] = stanza

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(client.StoragePasswords, "list", mock_storage_passwords_list)
    monkeypatch.setattr(
        client.StoragePasswords, "create", mock_storage_passwords_create
    )
    monkeypatch.setattr(
        client.StoragePasswords, "delete", mock_storage_passwords_delete
    )
    monkeypatch.setattr(client.StoragePassword, "delete", mock_storage_password_delete)
    monkeypatch.setattr(client.Configurations, "get", mock_configuration_get)
    monkeypatch.setattr(client.ConfigurationFile, "get", mock_configuration_file_get)
    monkeypatch.setattr(client.ConfigurationFile, "list", mock_configuration_file_list)
    monkeypatch.setattr(
        client.ConfigurationFile, "create", mock_configuration_file_create
    )
    monkeypatch.setattr(
        client.ConfigurationFile, "delete", mock_configuration_file_delete
    )
    monkeypatch.setattr(client.Stanza, "submit", mock_stanza_submit)

    cfm = conf_manager.ConfManager(common.SESSION_KEY, common.app)
    conf = cfm.get_conf("test")
    assert not conf.stanza_exist("test_stanza")
    conf.update("test_stanza", {"k1": 1, "k2": 2}, ["k1", "key_not_exist"])
    assert conf.get("test_stanza") == {
        "k2": 2,
        "k1": 1,
        "eai:access": common.record({"app": "test"}),
        "eai:appName": "test",
    }
    assert conf.get_all() == {
        "test_stanza": {
            "k2": 2,
            "k1": 1,
            "eai:access": common.record({"app": "test"}),
            "eai:appName": "test",
        }
    }

    conf.delete("test_stanza")
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.get("test_stanza")
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.delete("test_stanza")
    conf.reload()

    cfm = conf_manager.ConfManager(
        common.SESSION_KEY,
        common.app,
        realm=f"__REST_CREDENTIAL__#{common.app}#configs/conf-test",
    )
    conf = cfm.get_conf("test")
    assert not conf.stanza_exist("test_stanza")
    conf.update("test_stanza", {"k1": 1, "k2": 2}, ["k1", "key_not_exist"])
    assert conf.get("test_stanza") == {
        "k2": 2,
        "k1": 1,
        "eai:access": common.record({"app": "test"}),
        "eai:appName": "test",
    }
    assert conf.get_all() == {
        "test_stanza": {
            "k2": 2,
            "k1": 1,
            "eai:access": common.record({"app": "test"}),
            "eai:appName": "test",
        }
    }

    conf.delete("test_stanza")
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.get("test_stanza")
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.delete("test_stanza")
    conf.reload()


@mock.patch.object(conf_manager, "ConfManager")
def test_get_log_level_when_error_getting_conf(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    mock_conf_manager.get_conf.side_effect = conf_manager.ConfManagerException
    expected_log_level = "INFO"

    log_level = conf_manager.get_log_level(
        logger=mock.MagicMock(),
        session_key="session_key",
        app_name="app_name",
        conf_name="conf_name",
    )

    assert expected_log_level == log_level
