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

from solnlib import credentials


def test_credential_manager(monkeypatch):
    credentials_store = {}

    def mock_storage_passwords_list(self, count=None, **kwargs):
        return list(credentials_store.values())

    def mock_storage_passwords_create(self, password, username, realm=None):
        title = f"{realm}:{username}:" if realm else f":{username}:"
        password = client.StoragePassword(
            None,
            f"storage/passwords/{title}",
            state=record(
                {
                    "content": {
                        "clear_password": password,
                        "encr_password": hashlib.md5(password.encode("utf-8")).digest(),
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

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(client.StoragePasswords, "list", mock_storage_passwords_list)
    monkeypatch.setattr(
        client.StoragePasswords, "create", mock_storage_passwords_create
    )
    monkeypatch.setattr(
        client.StoragePasswords, "delete", mock_storage_passwords_delete
    )
    monkeypatch.setattr(client.StoragePassword, "delete", mock_storage_password_delete)

    cm = credentials.CredentialManager(
        common.SESSION_KEY, common.app, realm="realm_test"
    )
    cm.set_password("testuser1", "password1")
    assert cm.get_password("testuser1") == "password1"

    long_password = "".join(["1111111111" for i in range(30)])
    cm.set_password("testuser2", long_password)
    assert cm.get_password("testuser2") == long_password

    # change short password to long password
    long_password = "".join(["1111111111" for i in range(30)])
    cm.set_password("testuser1", long_password)
    assert cm.get_password("testuser1") == long_password

    # change to longer password
    longer_password = "".join(["1111111111" for i in range(120)])
    cm.set_password("testuser1", longer_password)
    assert cm.get_password("testuser1") == longer_password

    # change longer password to long password
    long_password = "".join(["1111111111" for i in range(30)])
    cm.set_password("testuser1", long_password)
    assert cm.get_password("testuser1") == long_password

    # change long password to short password
    cm.set_password("testuser1", "shortpwd")
    assert cm.get_password("testuser1") == "shortpwd"

    # password length  = 1
    cm.set_password("testuser1", "a")
    assert cm.get_password("testuser1") == "a"

    # password length = 255
    pwd_255 = "".join(["a" for i in range(255)])
    cm.set_password("testuser1", pwd_255)
    assert cm.get_password("testuser1") == pwd_255

    # password length = 256
    pwd_256 = "".join(["a" for i in range(256)])
    cm.set_password("testuser1", pwd_256)
    assert cm.get_password("testuser1") == pwd_256

    # password length = 255 * 2
    pwd_510 = "".join(["a" for i in range(510)])
    cm.set_password("testuser1", pwd_510)
    assert cm.get_password("testuser1") == pwd_510

    # password is empty
    cm.set_password("testuser1", "")
    assert cm.get_password("testuser1") == ""

    # password = '`'
    cm.set_password("testuser1", "`")
    assert cm.get_password("testuser1") == "`"

    # password is substring of END_MARK
    pwd_substr = "``splunk_cred_sep``S``splunk_cred_sep``P``"
    cm.set_password("testuser1", pwd_substr)
    assert cm.get_password("testuser1") == pwd_substr

    # test _update_password
    # Update a password which does not exist. create a new one.
    cm._update_password("testuser3", "beforechange")
    assert cm.get_password("testuser3") == "beforechange"

    # update an existed password
    cm._update_password("testuser3", "changed")
    assert cm.get_password("testuser3") == "changed"

    cm.delete_password("testuser1")
    with pytest.raises(Exception):
        cm.get_password("testuser1")

    cm.delete_password("testuser2")
    with pytest.raises(Exception):
        cm.get_password("testuser2")

    cm.delete_password("testuser3")
    with pytest.raises(Exception):
        cm.get_password("testuser3")


def test_get_session_key(monkeypatch):
    def _mock_session_key_post(self, url, headers=None, **kwargs):
        return common.make_response_record(
            '{"sessionKey":"' + common.SESSION_KEY + '"}'
        )

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.HttpLib, "post", _mock_session_key_post)

    assert credentials.get_session_key("user", "password") == common.SESSION_KEY

    with pytest.raises(ValueError):
        credentials.get_session_key("user", "password", scheme="non-http")
    credentials.get_session_key("user", "password", scheme="http")
    credentials.get_session_key("user", "password", scheme="https")
    with pytest.raises(ValueError):
        credentials.get_session_key("user", "password", scheme="http", host="==")
    credentials.get_session_key("user", "password", scheme="http", host="localhost")
    with pytest.raises(ValueError):
        credentials.get_session_key(
            "user", "password", scheme="http", host="localhost", port=-10
        )
    credentials.get_session_key(
        "user", "password", scheme="http", host="localhost", port=10
    )
    credentials.get_session_key("user", "password", scheme="HTTP")
    credentials.get_session_key("user", "password", scheme="HTTPS")


@mock.patch("splunklib.binding.HttpLib")
def test_get_session_key_when_503_error(mock_splunklib_httplib_class):
    mock_splunklib_httplib = mock_splunklib_httplib_class.return_value
    mock_splunklib_httplib.post.side_effect = binding.HTTPError(
        common.make_response_record(b"", status=503)
    )
    with pytest.raises(binding.HTTPError):
        credentials.get_session_key(
            "user",
            "password",
            "http",
            "localhost",
            8089,
        )
