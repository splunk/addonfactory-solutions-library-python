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

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import context

from solnlib import acl


def test_acl_manager():
    session_key = context.get_session_key()
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
