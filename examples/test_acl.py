# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

import sys
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import acl
from solnlib.credentials import get_session_key
import context


def test_acl_manager():
    session_key = get_session_key(
        context.username,
        context.password,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )

    aclm = acl.ACLManager(
        session_key,
        context.app,
        owner=context.owner,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )
    origin_perms = aclm.get("storage/collections/config/sessions/acl")

    perms = aclm.update(
        "storage/collections/config/sessions/acl",
        perms_read=["admin"],
        perms_write=["admin"],
    )

    origin_perms["perms"]["read"] = ["admin"]
    origin_perms["perms"]["write"] = ["admin"]
    assert origin_perms == perms
