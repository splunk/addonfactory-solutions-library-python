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

import json
import os.path as op
import sys
import time
import uuid

import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import context
from splunklib import binding, client
from splunklib.binding import HTTPError

from solnlib.credentials import get_session_key


def test_kvstore():
    session_key = get_session_key(
        context.username,
        context.password,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )
    kvstore = client.Service(
        scheme=context.scheme,
        host=context.host,
        port=context.port,
        token=session_key,
        app=context.app,
        owner=context.owner,
        autologin=True,
    ).kvstore
    fields = {"id": "string", "name": "string", "user": "string"}

    last_ex = None
    for i in range(3):
        try:
            kvstore.create("sessions", fields=fields)
            break
        except binding.HTTPError as e:
            last_ex = e
            time.sleep(2 ** (i + 1))
    else:
        if last_ex:
            raise last_ex

    collections = kvstore.list()
    collection_data = None
    for collection in collections:
        if collection.name == "sessions":
            collection_data = collection.data
            break
    assert collection_data

    record = {"id": uuid.uuid4().hex, "name": "session1", "user": "admin"}
    _key = collection_data.insert(json.dumps(record))["_key"]
    resp_record = collection_data.query_by_id(_key)
    resp_record = {
        key: resp_record[key] for key in resp_record if not key.startswith("_")
    }
    assert sorted(resp_record.values()) == sorted(record.values())

    record = {"id": uuid.uuid4().hex, "name": "session4", "user": "test"}
    collection_data.update(_key, json.dumps(record))
    resp_record = collection_data.query_by_id(_key)
    resp_record = {
        key: resp_record[key] for key in resp_record if not key.startswith("_")
    }
    assert sorted(resp_record.values()) == sorted(record.values())

    collection_data.delete_by_id(_key)
    with pytest.raises(HTTPError):
        collection_data.query_by_id(_key)
