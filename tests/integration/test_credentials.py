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
from typing import Optional
import pytest
from solnlib import credentials

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))


def _build_credential_manager(
    realm: Optional[str] = None,
) -> credentials.CredentialManager:
    session_key = credentials.get_session_key(
        context.username,
        context.password,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )
    return credentials.CredentialManager(
        session_key,
        context.app,
        owner=context.owner,
        realm=realm,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )


def test_get_password():
    cm = _build_credential_manager(realm=context.app)

    cm.set_password("user1", "password1")
    assert cm.get_password("user1") == "password1"


def test_get_password_when_no_user_exists_then_throw_exception():
    cm = _build_credential_manager(realm=context.app)

    with pytest.raises(credentials.CredentialNotExistException):
        cm.get_password("nonexistentuser")


def test_delete_password():
    cm = _build_credential_manager(realm=context.app)
    cm.set_password("user2", "password2")

    cm.delete_password("user2")

    with pytest.raises(credentials.CredentialNotExistException):
        cm.get_password("user2")


def test_delete_password_when_no_user_exists_then_throw_exception():
    cm = _build_credential_manager(realm=context.app)

    with pytest.raises(credentials.CredentialNotExistException):
        cm.delete_password("nonexistentuser")


def test_get_clear_passwords_in_realm():
    cm = _build_credential_manager(realm=context.app)
    cm.set_password("user3", "password3")

    expected_result = {
        "name": "solnlib_demo:user3",
        "realm": "solnlib_demo",
        "username": "user3",
        "clear_password": "password3",
    }
    results = cm.get_clear_passwords_in_realm()
    for result in results:
        if result["name"] == expected_result["name"]:
            assert result["realm"] == expected_result["realm"]
            assert result["username"] == expected_result["username"]
            assert result["clear_password"] == expected_result["clear_password"]
            break


def test_get_clear_passwords():
    cm = _build_credential_manager()
    cm.set_password("user3", "password3")

    expected_result = {
        "name": "solnlib_demo:user3",
        "realm": "solnlib_demo",
        "username": "user3",
        "clear_password": "password3",
    }
    results = cm.get_clear_passwords()
    for result in results:
        if result["name"] == expected_result["name"]:
            assert result["realm"] == expected_result["realm"]
            assert result["username"] == expected_result["username"]
            assert result["clear_password"] == expected_result["clear_password"]
            break
