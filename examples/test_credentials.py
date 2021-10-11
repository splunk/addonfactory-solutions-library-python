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

import os.path as op
import sys

import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import context

from solnlib import credentials


def test_credential_manager():
    session_key = credentials.get_session_key(
        context.username,
        context.password,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )

    cm = credentials.CredentialManager(
        session_key,
        context.app,
        owner=context.owner,
        realm=context.app,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )

    cm.set_password("testuser1", "password1")
    assert cm.get_password("testuser1") == "password1"

    long_password = "".join(["1111111111" for i in range(30)])
    cm.set_password("testuser2", long_password)
    assert cm.get_password("testuser2") == long_password

    cm.delete_password("testuser1")
    with pytest.raises(credentials.CredentialNotExistException):
        cm.get_password("testuser1")

    cm.delete_password("testuser2")
    with pytest.raises(credentials.CredentialNotExistException):
        cm.get_password("testuser2")
