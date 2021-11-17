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

from solnlib import conf_manager


def test_conf_manager():
    session_key = context.get_session_key()
    cfm = conf_manager.ConfManager(
        session_key,
        context.app,
        owner=context.owner,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )

    try:
        conf = cfm.get_conf("test")
    except conf_manager.ConfManagerException:
        conf = cfm.create_conf("test")

    assert not conf.stanza_exist("test_stanza")
    conf.update("test_stanza", {"k1": 1, "k2": 2}, ["k1"])
    assert conf.get("test_stanza")["k1"] == 1
    assert int(conf.get("test_stanza")["k2"]) == 2
    assert conf.get("test_stanza")["eai:appName"] == "solnlib_demo"
    assert len(conf.get_all()) == 1
    conf.delete("test_stanza")
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.get("test_stanza")
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.delete("test_stanza")
    conf.reload()
