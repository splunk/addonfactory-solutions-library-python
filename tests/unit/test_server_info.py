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
import common
import pytest
from splunklib import binding

from solnlib import server_info


def test_from_server_uri():
    server_info.ServerInfo.from_server_uri("https://localhost:8089", common.SESSION_KEY)


def test_from_server_uri_when_invalid_server_uri():
    with pytest.raises(ValueError):
        server_info.ServerInfo.from_server_uri(
            "no-schema://localhost:99999", common.SESSION_KEY
        )


class TestServerInfo:
    def test_get_shc_members(self, monkeypatch):
        def _mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
            return common.make_response_record(
                '{"entry": [{"name": "5B4A53C7-B824-4103-B8CC-C22E1EC6480F", '
                '"content": '
                '{"peer_scheme_host_port": "https://192.168.1.85:8089", "label": "SHC01_SearchHead02_1_85"}}, '
                '{"name": "D7E3BA03-85CE-449A-9736-38F2DA58236B", "content": '
                '{"peer_scheme_host_port": "https://192.168.1.86:8089", "label": "SHC01_SearchHead03_1_86"}}, '
                '{"name": "DA72938A-72C4-46F3-86BE-2E200EC56C76", "content": {"peer_scheme_host_port": '
                '"https://192.168.1.84:8089", "label": "SHC01_SearchHead01_1_84"}}]}'
            )

        common.mock_splunkhome(monkeypatch)
        common.mock_serverinfo(monkeypatch)
        monkeypatch.setattr(binding.Context, "get", _mock_get)

        si = server_info.ServerInfo(common.SESSION_KEY)
        assert si.get_shc_members() == [
            ("SHC01_SearchHead02_1_85", "https://192.168.1.85:8089"),
            ("SHC01_SearchHead03_1_86", "https://192.168.1.86:8089"),
            ("SHC01_SearchHead01_1_84", "https://192.168.1.84:8089"),
        ]

    def test_is_captain_ready(self, monkeypatch):
        def _mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
            msg = (
                '{"entry": [{"content": {"eai:acl": null,"elected_captain": 1463195590,'
                '"id": "9CA04BAD-0C24-4703-8A88-E20345833508","initialized_flag": true,'
                '"label": "ta-shc04-sh2","maintenance_mode": false,"mgmt_uri": "https://ta-shc04-sh2:8089",'
                '"min_peers_joined_flag": true,"peer_scheme_host_port": "https://ta-shc04-sh2:8089",'
                '"rolling_restart_flag": false,"service_ready_flag": true,"start_time": 1463195526}}]}'
            )
            return common.make_response_record(msg)

        common.mock_splunkhome(monkeypatch)
        common.mock_serverinfo(monkeypatch)
        monkeypatch.setattr(binding.Context, "get", _mock_get)

        si = server_info.ServerInfo(common.SESSION_KEY)
        assert si.is_captain_ready()
