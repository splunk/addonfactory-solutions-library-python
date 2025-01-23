#
# Copyright 2025 Splunk Inc.
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

import pytest
from solnlib.bulletin_rest_client import BulletinRestClient


context = {"owner": "nobody", "scheme": "https", "host": "localhost", "port": 8089}


def test_create_message(monkeypatch):
    session_key = "123"
    bulletin_client = BulletinRestClient(
        "msg_name_1",
        session_key,
        "_",
        **context,
    )

    def new_post(*args, **kwargs) -> str:
        return "ok"

    monkeypatch.setattr(bulletin_client._rest_client, "post", new_post)

    bulletin_client.create_message(
        "new message to bulletin",
        capabilities=["apps_restore", "delete_messages"],
        roles=["admin"],
    )

    with pytest.raises(ValueError, match="Severity must be one of"):
        bulletin_client.create_message(
            "new message to bulletin",
            severity="debug",
            capabilities=["apps_restore", "delete_messages", 1],
            roles=["admin"],
        )

    with pytest.raises(ValueError, match="Capabilities must be a list of strings."):
        bulletin_client.create_message(
            "new message to bulletin",
            capabilities=["apps_restore", "delete_messages", 1],
            roles=["admin"],
        )

    with pytest.raises(ValueError, match="Roles must be a list of strings."):
        bulletin_client.create_message(
            "new message to bulletin",
            capabilities=["apps_restore", "delete_messages"],
            roles=["admin", 1],
        )
