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

import os.path as op
import sys

import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import context

from solnlib import user_access


def test_object_acl_manager():
    session_key = context.get_session_key()
    oaclm = user_access.ObjectACLManager(
        "object_acls_collection",
        session_key,
        context.app,
        owner=context.owner,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
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
        obj_collection, obj_id1, obj_type, context.app, context.owner, obj_perms1, True
    )
    oaclm.update_acl(
        obj_collection,
        obj_id1,
        obj_type,
        context.app,
        context.owner,
        obj_perms2,
        True,
        replace_existing=False,
    )
    obj_acl = oaclm.get_acl(obj_collection, obj_id1)
    assert set(obj_acl.obj_perms["read"]) == {"admin", "user1"}

    oaclm.update_acls(
        obj_collection,
        [obj_id2, obj_id3],
        obj_type,
        context.app,
        context.owner,
        obj_perms1,
        True,
    )
    oaclm.get_acl(obj_collection, obj_id2)
    oaclm.get_acl(obj_collection, obj_id3)
    obj_acls = oaclm.get_acls(obj_collection, [obj_id2, obj_id3, obj_id4])
    assert len(obj_acls) == 2

    assert oaclm.get_accessible_object_ids(
        "user1", "read", obj_collection, [obj_id1, obj_id2, obj_id3]
    ) == [obj_id1]

    oaclm.delete_acl(obj_collection, obj_id1)
    oaclm.delete_acls(obj_collection, [obj_id2, obj_id3])


def test_app_capability_manager():
    session_key = context.get_session_key()
    acm = user_access.AppCapabilityManager(
        "app_capabilities_collection",
        session_key,
        context.app,
        owner=context.owner,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
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
    acm.register_capabilities(app_capabilities)
    assert acm.capabilities_are_registered()
    assert acm.get_capabilities() == app_capabilities
    acm.unregister_capabilities()
    assert not acm.capabilities_are_registered()


def test_check_user_access():
    session_key = context.get_session_key()
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
            session_key, app_capabilities, "object_type1", "read"
        )


def test_get_current_username():
    session_key = context.get_session_key()
    assert (
        user_access.get_current_username(
            session_key, scheme=context.scheme, host=context.host, port=context.port
        )
        == context.username
    )


def test_get_user_capabilities():
    session_key = context.get_session_key()
    user_access.get_user_capabilities(
        session_key,
        context.username,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )


def test_user_is_capable():
    session_key = context.get_session_key()
    assert not user_access.user_is_capable(
        session_key,
        context.username,
        "test_capability",
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )


def test_get_user_roles():
    session_key = context.get_session_key()
    user_access.get_user_roles(
        session_key,
        context.username,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )


def test_user_access():
    test_object_acl_manager()
    test_app_capability_manager()
    test_check_user_access()
    test_get_current_username()
    test_get_user_capabilities()
    test_user_is_capable()
    test_get_user_roles()
