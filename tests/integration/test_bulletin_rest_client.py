#
# Copyright 2024 Splunk Inc.
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
from splunklib import binding
import pytest
from solnlib import bulletin_rest_client as brc


def _build_bulletin_manager(msg_name, session_key: str) -> brc.BulletinRestClient:
    return brc.BulletinRestClient(
        msg_name,
        session_key,
        "-",
        owner=context.owner,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )


def test_create_message():
    session_key = context.get_session_key()
    bulletin_client = _build_bulletin_manager("msg_name", session_key)

    with pytest.raises(binding.HTTPError) as e:
        bulletin_client.create_message(
            "new message to bulletin",
            capabilities=["apps_restore", "unknown_cap"],
            roles=["admin"],
        )
    assert str(e.value.status) == "400"

    with pytest.raises(binding.HTTPError) as e:
        bulletin_client.create_message(
            "new message to bulletin", roles=["unknown_role"]
        )
    assert str(e.value.status) == "400"


def test_bulletin_rest_api():
    session_key = context.get_session_key()
    bulletin_client_1 = _build_bulletin_manager("msg_name_1", session_key)
    bulletin_client_2 = _build_bulletin_manager("msg_name_2", session_key)

    # clear bulletin before tests
    _clear_bulletin()

    bulletin_client_1.create_message(
        "new message to bulletin",
        capabilities=["apps_restore", "edit_roles"],
        roles=["admin"],
    )

    get_msg_1 = bulletin_client_1.get_message()
    assert get_msg_1["entry"][0]["content"]["message"] == "new message to bulletin"
    assert get_msg_1["entry"][0]["content"]["severity"] == "warn"

    bulletin_client_1.create_message(
        "new message to bulletin", bulletin_client_1.Severity.INFO
    )
    get_msg_1 = bulletin_client_1.get_message()
    assert get_msg_1["entry"][0]["content"]["severity"] == "info"

    bulletin_client_1.create_message(
        "new message to bulletin", bulletin_client_1.Severity.ERROR
    )
    get_msg_1 = bulletin_client_1.get_message()
    assert get_msg_1["entry"][0]["content"]["severity"] == "error"

    get_all_msg = bulletin_client_1.get_all_messages()
    assert len(get_all_msg["entry"]) == 1

    bulletin_client_2.create_message("new message to bulletin 2")

    get_msg_2 = bulletin_client_2.get_message()
    assert get_msg_2["entry"][0]["content"]["message"] == "new message to bulletin 2"

    get_all_msg = bulletin_client_1.get_all_messages()
    assert len(get_all_msg["entry"]) == 2

    bulletin_client_1.delete_message()

    with pytest.raises(binding.HTTPError) as e:
        bulletin_client_1.get_message()
    assert str(e.value.status) == "404"

    with pytest.raises(binding.HTTPError) as e:
        bulletin_client_1.delete_message()
    assert str(e.value.status) == "404"

    get_all_msg = bulletin_client_1.get_all_messages()
    assert len(get_all_msg["entry"]) == 1

    bulletin_client_2.delete_message()

    get_all_msg = bulletin_client_1.get_all_messages()
    assert len(get_all_msg["entry"]) == 0


def _clear_bulletin():
    session_key = context.get_session_key()
    bulletin_client = _build_bulletin_manager("", session_key)

    msg_to_del = [el["name"] for el in bulletin_client.get_all_messages()["entry"]]
    for msg in msg_to_del:
        endpoint = f"{bulletin_client.MESSAGES_ENDPOINT}/{msg}"
        bulletin_client._rest_client.delete(endpoint)
