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
import os
import tempfile
from unittest import mock

import pytest
from fakes.fake_kv_store_collection_data import (
    FakeKVStoreCollectionData,
    FakeKVStoreCollectionDataThrowingExceptions,
)
from splunklib import client

from solnlib.modular_input import (
    CheckpointerException,
    FileCheckpointer,
    KVStoreCheckpointer,
)


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_when_cannot_initialize_collection(
    mock_get_collection_data,
):
    mock_get_collection_data.side_effect = KeyError
    with pytest.raises(CheckpointerException):
        _ = KVStoreCheckpointer("collection_name", "session_name", "app")


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_get_when_splunkd_error(mock_get_collection_data):
    mock_get_collection_data.return_value = (
        FakeKVStoreCollectionDataThrowingExceptions()
    )
    checkpoint = KVStoreCheckpointer("collection_name", "session_key", "app")
    with pytest.raises(client.HTTPError):
        _ = checkpoint.get("key")


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_delete_when_splunkd_error(mock_get_collection_data):
    mock_get_collection_data.return_value = (
        FakeKVStoreCollectionDataThrowingExceptions()
    )
    checkpoint = KVStoreCheckpointer("collection_name", "session_key", "app")
    with pytest.raises(client.HTTPError):
        _ = checkpoint.delete("key")


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_get_when_no_data(mock_get_collection_data):
    mock_get_collection_data.return_value = FakeKVStoreCollectionData()
    checkpoint = KVStoreCheckpointer("collection_name", "session_key", "app")
    assert not checkpoint.get("key_with_no_data")


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_get_data_exists(mock_get_collection_data):
    documents = [
        {"_key": "key_with_string_data", "state": "some_state"},
        {"_key": "key_with_dict_data", "state": {"k": "v"}},
    ]
    fake = FakeKVStoreCollectionData(documents)
    mock_get_collection_data.return_value = fake
    checkpoint = KVStoreCheckpointer("collection_name", "session_key", "app")
    assert "some_state" == checkpoint.get("key_with_string_data")


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_delete_when_no_data(mock_get_collection_data):
    mock_get_collection_data.return_value = FakeKVStoreCollectionData()
    checkpoint = KVStoreCheckpointer("collection_name", "session_key", "app")
    assert not checkpoint.delete("key_with_no_data")


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_delete_data_exists(mock_get_collection_data):
    documents = [
        {"_key": "key_with_string_data", "state": "some_state"},
        {"_key": "key_with_dict_data", "state": {"k": "v"}},
    ]
    fake_kv_store_collection_data = FakeKVStoreCollectionData(documents)
    mock_get_collection_data.return_value = fake_kv_store_collection_data
    checkpoint = KVStoreCheckpointer("collection_name", "session_key", "app")
    checkpoint.delete("key_with_string_data")
    assert fake_kv_store_collection_data.id_exists("key_with_string_data") is False
    assert not checkpoint.get("key_with_string_data")


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_update_key_that_does_not_exist(mock_get_collection_data):
    documents = [
        {"_key": "key_with_string_data", "state": "some_state"},
        {"_key": "key_with_dict_data", "state": {"k": "v"}},
    ]
    fake_kv_store_collection_data = FakeKVStoreCollectionData(documents)
    mock_get_collection_data.return_value = fake_kv_store_collection_data
    checkpoint = KVStoreCheckpointer("collection_name", "session_key", "app")
    checkpoint.update("key_with_integer_data", 5)
    assert 5 == checkpoint.get("key_with_integer_data")


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_update_key_that_already_exists(mock_get_collection_data):
    documents = [
        {"_key": "key_with_string_data", "state": "some_state"},
        {"_key": "key_with_dict_data", "state": {"k": "v"}},
    ]
    fake_kv_store_collection_data = FakeKVStoreCollectionData(documents)
    mock_get_collection_data.return_value = fake_kv_store_collection_data
    checkpoint = KVStoreCheckpointer("collection_name", "session_key", "app")
    checkpoint.update("key_with_dict_data", {"integer": 10})
    assert {"integer": 10} == checkpoint.get("key_with_dict_data")


@mock.patch("solnlib._utils.get_collection_data")
def test_kvstore_checkpointer_batch_update(mock_get_collection_data):
    documents = [
        {"_key": "key_with_string_data", "state": "some_state"},
        {"_key": "key_with_dict_data", "state": {"k": "v"}},
    ]
    fake_kv_store_collection_data = FakeKVStoreCollectionData(documents)
    mock_get_collection_data.return_value = fake_kv_store_collection_data
    checkpoint = KVStoreCheckpointer("collection_name", "session_key", "app")
    states = [
        {"_key": "key_with_dict_data", "state": {"integer": 10}},
        {"_key": "key_with_integer_data", "state": 2},
    ]
    checkpoint.batch_update(states)
    assert {"integer": 10} == checkpoint.get("key_with_dict_data")
    assert 2 == checkpoint.get("key_with_integer_data")


def test_file_checkpointer_update_when_key_exists():
    with tempfile.TemporaryDirectory() as tmpdirname:
        checkpointer = FileCheckpointer(tmpdirname)
        # "a2V5XzE=" - encoded value for "key_1"
        with open(os.path.join(tmpdirname, "a2V5XzE="), "w") as f:
            json.dump("content", f)
        checkpointer.update("key_1", "updated_content")
        # "a2V5XzE=" - encoded value for "key_1"
        with open(os.path.join(tmpdirname, "a2V5XzE=")) as f:
            new_content = f.read()
        assert new_content == '"updated_content"'


@mock.patch("os.remove")
def test_file_checkpointer_update_when_os_error(mock_os_remove):
    with tempfile.TemporaryDirectory() as tmpdirname:
        checkpointer = FileCheckpointer(tmpdirname)
        mock_os_remove.side_effect = OSError
        # "a2V5XzE=" - encoded value for "key_1"
        with open(os.path.join(tmpdirname, "a2V5XzE="), "w") as f:
            json.dump("content", f)
        checkpointer.update("key_1", "updated_content")
        # "a2V5XzE=" - encoded value for "key_1"
        with open(os.path.join(tmpdirname, "a2V5XzE=")) as f:
            new_content = f.read()
        assert new_content == '"updated_content"'


def test_file_checkpointer_update_when_key_does_not_exist():
    with tempfile.TemporaryDirectory() as tmpdirname:
        checkpointer = FileCheckpointer(tmpdirname)
        checkpointer.update("key_1", "updated_content")
        # "a2V5XzE=" - encoded value for "key_1"
        with open(os.path.join(tmpdirname, "a2V5XzE=")) as f:
            new_content = f.read()
        assert new_content == '"updated_content"'


def test_file_checkpointer_batch_update():
    with tempfile.TemporaryDirectory() as tmpdirname:
        checkpointer = FileCheckpointer(tmpdirname)
        # "a2V5XzE=" - encoded value for "key_1"
        with open(os.path.join(tmpdirname, "a2V5XzE="), "w") as f:
            json.dump("content1", f)
        # "a2V5XzI=" - encoded value for "key_2"
        with open(os.path.join(tmpdirname, "a2V5XzI="), "w") as f:
            json.dump("content1", f)
        states = [
            {"_key": "key_1", "state": "updated_content1"},
            {"_key": "key_3", "state": "content3"},
        ]
        checkpointer.batch_update(states)
        # "a2V5XzE=" - encoded value for "key_1"
        with open(os.path.join(tmpdirname, "a2V5XzE=")) as f:
            new_content = f.read()
        assert new_content == '"updated_content1"'
        # "a2V5XzM=" - encoded value for "key_3"
        with open(os.path.join(tmpdirname, "a2V5XzM=")) as f:
            new_content = f.read()
        assert new_content == '"content3"'


def test_file_checkpointer_get_when_key_exists():
    with tempfile.TemporaryDirectory() as tmpdirname:
        checkpointer = FileCheckpointer(tmpdirname)
        # "a2V5XzE=" - encoded value for "key_1"
        with open(os.path.join(tmpdirname, "a2V5XzE="), "w") as f:
            json.dump("content", f)
        assert "content" == checkpointer.get("key_1")


def test_file_checkpointer_get_when_key_does_not_exist():
    with tempfile.TemporaryDirectory() as tmpdirname:
        checkpointer = FileCheckpointer(tmpdirname)
        checkpointer.get("key_that_does_not_exist")


def test_file_checkpointer_delete_when_key_exists():
    with tempfile.TemporaryDirectory() as tmpdirname:
        checkpointer = FileCheckpointer(tmpdirname)
        # "a2V5XzE=" - encoded value for "key_1"
        with open(os.path.join(tmpdirname, "a2V5XzE="), "w") as f:
            json.dump("content", f)
        checkpointer.delete("key_1")


def test_file_checkpointer_delete_when_key_does_not_exist():
    with tempfile.TemporaryDirectory() as tmpdirname:
        checkpointer = FileCheckpointer(tmpdirname)
        checkpointer.delete("key_that_does_not_exist")
