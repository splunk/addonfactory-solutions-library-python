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

import common
import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunklib import binding, client

from solnlib import user_access


def test_object_acl_manager(monkeypatch):
    OBJECT_ACLS_COLLECTION_NAME = "object_acls_collection"

    object_acls = {}

    def mock_kvstore_collections_get(
        self, name="", owner=None, app=None, sharing=None, **query
    ):
        raise binding.HTTPError(common.make_response_record("", status=404))

    def mock_kvstore_collections_create(self, name, indexes={}, fields={}, **kwargs):
        pass

    def mock_kvstore_collections_list(self, count=None, **kwargs):
        return [client.KVStoreCollection(None, None)]

    def mock_kvstore_collection_init(self, service, path, **kwargs):
        pass

    def mock_kvstore_collection_data_init(self, collection):
        pass

    def mock_kvstore_collection_data_batch_save(self, *documents):
        for document in documents:
            object_acls[document["_key"]] = document

    def mock_kvstore_collection_data_query_by_id(self, id):
        try:
            return object_acls[id]
        except:
            raise binding.HTTPError(common.make_response_record("", status=404))

    def mock_kvstore_collection_data_query(self, **query):
        query = json.loads(query["query"])
        keys = query["$or"]
        keys = [key["_key"] for key in keys]
        records = []
        for key in keys:
            if key in object_acls:
                records.append(object_acls[key])
        return records

    def mock_kvstore_collection_data_delete_by_id(self, id):
        try:
            del object_acls[id]
        except:
            raise binding.HTTPError(common.make_response_record("", status=404))

    def mock_kvstore_collection_data_delete(self, query=None):
        query = json.loads(query)
        keys = query["$or"]
        keys = [key["_key"] for key in keys]
        for key in keys:
            if key in object_acls:
                del object_acls[key]

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(client.KVStoreCollections, "get", mock_kvstore_collections_get)
    monkeypatch.setattr(
        client.KVStoreCollections, "create", mock_kvstore_collections_create
    )
    monkeypatch.setattr(
        client.KVStoreCollections, "list", mock_kvstore_collections_list
    )
    monkeypatch.setattr(
        client.KVStoreCollection, "__init__", mock_kvstore_collection_init
    )
    monkeypatch.setattr(
        client.KVStoreCollection,
        "name",
        "Splunk_TA_test" + "_" + OBJECT_ACLS_COLLECTION_NAME,
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData, "__init__", mock_kvstore_collection_data_init
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData,
        "batch_save",
        mock_kvstore_collection_data_batch_save,
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData,
        "query_by_id",
        mock_kvstore_collection_data_query_by_id,
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData, "query", mock_kvstore_collection_data_query
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData,
        "delete_by_id",
        mock_kvstore_collection_data_delete_by_id,
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData, "delete", mock_kvstore_collection_data_delete
    )

    oaclm = user_access.ObjectACLManager(
        OBJECT_ACLS_COLLECTION_NAME, common.SESSION_KEY, "Splunk_TA_test"
    )

    obj_collection = "test_object_collection"
    obj_id1 = "281a6d3310e711e6b2c9a45e60e34295"
    obj_id2 = "281a6d3310e711e6b2c9a45e60e34296"
    obj_id3 = "281a6d3310e711e6b2c9a45e60e34297"
    obj_id4 = "281a6d3310e711e6b2c9a45e60e34294"
    obj_type = "test_object_type"
    obj_perms1 = {"read": ["admin"], "write": ["admin"], "delete": ["admin"]}
    obj_perms2 = {"read": ["user1"], "write": ["admin"], "delete": ["admin"]}
    oaclm.update_acl(
        obj_collection, obj_id1, obj_type, "Splunk_TA_test", "nobody", obj_perms1, True
    )
    oaclm.update_acl(
        obj_collection,
        obj_id1,
        obj_type,
        "Splunk_TA_test",
        "nobody",
        obj_perms2,
        True,
        replace_existing=False,
    )
    obj_acl = oaclm.get_acl(obj_collection, obj_id1)
    assert obj_acl.obj_collection == "test_object_collection"
    assert obj_acl.obj_id == obj_id1
    assert obj_acl.obj_type == "test_object_type"
    assert obj_acl.obj_app == "Splunk_TA_test"
    assert obj_acl.obj_owner == "nobody"
    assert obj_acl.obj_shared_by_inclusion == True
    assert sorted(obj_acl.obj_perms["read"]) == ["admin", "user1"]

    oaclm.update_acls(
        obj_collection,
        [obj_id2, obj_id3],
        obj_type,
        "Splunk_TA_test",
        "nobody",
        obj_perms1,
        True,
        replace_existing=False,
    )
    oaclm.get_acl(obj_collection, obj_id2)
    oaclm.get_acl(obj_collection, obj_id3)
    obj_acls = oaclm.get_acls(obj_collection, [obj_id2, obj_id3, obj_id4])
    assert len(obj_acls) == 2

    assert oaclm.get_accessible_object_ids(
        "user1", "read", obj_collection, [obj_id1, obj_id2, obj_id3]
    ) == [obj_id1]

    oaclm.delete_acl(obj_collection, obj_id1)
    with pytest.raises(user_access.ObjectACLNotExistException):
        oaclm.delete_acl(obj_collection, obj_id1)
    oaclm.delete_acls(obj_collection, [obj_id2, obj_id3])

    assert not object_acls


def test_app_capability_manager(monkeypatch):
    APP_CAPABILITIES_COLLECTION_NAME = "app_capabilities_collection"

    app_capabilities = {}

    def mock_kvstore_collections_get(
        self, name="", owner=None, app=None, sharing=None, **query
    ):
        raise binding.HTTPError(common.make_response_record("", status=404))

    def mock_kvstore_collections_create(self, name, indexes={}, fields={}, **kwargs):
        pass

    def mock_kvstore_collections_list(self, count=None, **kwargs):
        return [client.KVStoreCollection(None, None)]

    def mock_kvstore_collection_init(self, service, path, **kwargs):
        pass

    def mock_kvstore_collection_data_init(self, collection):
        pass

    def mock_kvstore_collection_data_batch_save(self, *documents):
        for document in documents:
            app_capabilities[document["_key"]] = document

    def mock_kvstore_collection_data_query_by_id(self, id):
        try:
            return app_capabilities[id]
        except:
            raise binding.HTTPError(common.make_response_record("", status=404))

    def mock_kvstore_collection_data_delete_by_id(self, id):
        try:
            del app_capabilities[id]
        except:
            raise binding.HTTPError(None, status=404)

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(client.KVStoreCollections, "get", mock_kvstore_collections_get)
    monkeypatch.setattr(
        client.KVStoreCollections, "create", mock_kvstore_collections_create
    )
    monkeypatch.setattr(
        client.KVStoreCollections, "list", mock_kvstore_collections_list
    )
    monkeypatch.setattr(
        client.KVStoreCollection, "__init__", mock_kvstore_collection_init
    )
    monkeypatch.setattr(
        client.KVStoreCollection,
        "name",
        "Splunk_TA_test" + "_" + APP_CAPABILITIES_COLLECTION_NAME,
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData, "__init__", mock_kvstore_collection_data_init
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData,
        "batch_save",
        mock_kvstore_collection_data_batch_save,
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData,
        "query_by_id",
        mock_kvstore_collection_data_query_by_id,
    )
    monkeypatch.setattr(
        client.KVStoreCollectionData,
        "delete_by_id",
        mock_kvstore_collection_data_delete_by_id,
    )

    acm = user_access.AppCapabilityManager(
        APP_CAPABILITIES_COLLECTION_NAME, common.SESSION_KEY, "Splunk_TA_test"
    )

    app_capabilities = {
        "object_type1": {
            "read": "read_app_object_type1",
            "write": "write_app_object_type1",
            "delete": "delete_app_object_type1",
        },
        "object_type2": {
            "read": "read_app_object_type2",
            "write": "write_app_object_type2",
            "delete": "delete_app_object_type2",
        },
    }

    with pytest.raises(user_access.AppCapabilityNotExistException):
        acm.get_capabilities()
    acm.register_capabilities(app_capabilities)
    assert acm.capabilities_are_registered()
    assert acm.get_capabilities() == app_capabilities
    acm.unregister_capabilities()
    assert not acm.capabilities_are_registered()


def test_check_user_access(monkeypatch):
    def mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
        if path_segment.endswith("current-context"):
            return common.make_response_record(
                '{"entry": [{"content": {"username": "admin"}}]}'
            )
        else:
            return common.make_response_record(
                '{"entry": [{"content": {"capabilities": ["can_read"]}}]}'
            )

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.Context, "get", mock_get)

    app_capabilities = {
        "object_type1": {
            "read": "read_app_object_type1",
            "write": "write_app_object_type1",
            "delete": "delete_app_object_type1",
        },
        "object_type2": {
            "read": "read_app_object_type2",
            "write": "write_app_object_type2",
            "delete": "delete_app_object_type2",
        },
    }

    with pytest.raises(user_access.UserAccessException):
        user_access.check_user_access(
            common.SESSION_KEY, app_capabilities, "object_type1", "read"
        )


def test_get_current_username(monkeypatch):
    mode = 0

    def mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
        if mode == 0:
            return common.make_response_record(
                '{"entry": [{"content": {"username": "admin"}}]}'
            )
        else:
            raise binding.HTTPError(common.make_response_record("", status=401))

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.Context, "get", mock_get)

    assert user_access.get_current_username(common.SESSION_KEY) == "admin"

    mode = 1
    with pytest.raises(user_access.InvalidSessionKeyException):
        user_access.get_current_username(common.SESSION_KEY)


def test_get_user_capabilities(monkeypatch):
    mode = 0

    def mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
        if mode == 0:
            return common.make_response_record(
                '{"entry": [{"content": {"capabilities": ["can_read"]}}]}'
            )
        else:
            raise binding.HTTPError(common.make_response_record("", status=404))

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.Context, "get", mock_get)

    assert user_access.get_user_capabilities(common.SESSION_KEY, "admin") == [
        "can_read"
    ]

    mode = 1
    with pytest.raises(user_access.UserNotExistException):
        user_access.get_user_capabilities(common.SESSION_KEY, "admin")


def test_user_is_capable(monkeypatch):
    mode = 0

    def mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
        if mode == 0:
            return common.make_response_record(
                '{"entry": [{"content": {"capabilities": ["can_read"]}}]}'
            )
        else:
            raise binding.HTTPError(common.make_response_record("", status=404))

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.Context, "get", mock_get)

    assert not user_access.user_is_capable(
        common.SESSION_KEY, "admin", "test_capability"
    )

    mode = 1
    with pytest.raises(user_access.UserNotExistException):
        user_access.user_is_capable(common.SESSION_KEY, "admin", "test_capability")


def test_get_user_roles(monkeypatch):
    mode = 0

    def mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
        if mode == 0:
            return common.make_response_record(
                '{"entry": [{"content": {"roles": ["admin", "user"]}}]}'
            )
        else:
            raise binding.HTTPError(common.make_response_record("", status=404))

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.Context, "get", mock_get)

    user_access.get_user_roles(common.SESSION_KEY, "admin") == ["admin", "user"]

    mode = 1
    with pytest.raises(user_access.UserNotExistException):
        user_access.get_user_roles(common.SESSION_KEY, "admin")
