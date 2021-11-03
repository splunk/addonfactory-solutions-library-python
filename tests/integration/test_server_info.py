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
import context
import pytest

from solnlib import server_info


def test_server_info_methods():
    # This test does not check for guid, version and SHC related methods.
    session_key = context.get_session_key()
    si = server_info.ServerInfo(session_key, context.scheme, context.host, context.port)
    assert "custom-servername" == si.server_name
    assert si.is_search_head() is False
    assert si.is_shc_member() is False
    with pytest.raises(server_info.ServerInfoException):
        si.get_shc_members()
    with pytest.raises(server_info.ServerInfoException):
        si.captain_info()
    with pytest.raises(server_info.ServerInfoException):
        si.is_captain_ready()
    assert si.is_captain() is False
    assert si.is_cloud_instance() is False


def test_from_server_uri():
    session_key = context.get_session_key()
    si = server_info.ServerInfo.from_server_uri(
        f"{context.scheme}://{context.host}:{context.port}", session_key
    )
    # Run 1 small test to check that .from_server_uri is working.
    assert "custom-servername" == si.server_name
