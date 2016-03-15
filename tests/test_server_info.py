import sys
import os.path as op

from splunklib import binding

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import server_info


class TestServerInfo(object):
    _normal_server_info = '{"entry": [{"content": {"server_roles": ["cluster_search_head", "search_head", "kv_store", "shc_captain"], "version": "6.3.1511.2"}}]}'

    _shc_server_info = '{"entry": [{"name": "5B4A53C7-B824-4103-B8CC-C22E1EC6480F", "content": {"peer_scheme_host_port": "https://192.168.1.85:8089", "label": "SHC01_SearchHead02_1_85"}}, {"name": "D7E3BA03-85CE-449A-9736-38F2DA58236B", "content": {"peer_scheme_host_port": "https://192.168.1.86:8089", "label": "SHC01_SearchHead03_1_86"}}, {"name": "DA72938A-72C4-46F3-86BE-2E200EC56C76", "content": {"peer_scheme_host_port": "https://192.168.1.84:8089", "label": "SHC01_SearchHead01_1_84"}}]}'

    def _mock_server_info_get(self, path_segment, owner=None, app=None,
                              sharing=None, **query):
        if path_segment == '/services/server/info/server-info':
            server_info = self._normal_server_info
        else:
            server_info = self._shc_server_info

        return common.make_response_record(server_info)

    def test_is_captain(self, monkeypatch):
        monkeypatch.setattr(binding.Context, 'get', self._mock_server_info_get)

        si = server_info.ServerInfo(common.SESSION_KEY)
        assert si.is_captain()

    def test_is_cloud_instance(self, monkeypatch):
        monkeypatch.setattr(binding.Context, 'get', self._mock_server_info_get)

        si = server_info.ServerInfo(common.SESSION_KEY)
        assert not si.is_cloud_instance()

    def test_is_search_head(self, monkeypatch):
        monkeypatch.setattr(binding.Context, 'get', self._mock_server_info_get)

        si = server_info.ServerInfo(common.SESSION_KEY)
        assert si.is_search_head()

    def test_is_shc_member(self, monkeypatch):
        monkeypatch.setattr(binding.Context, 'get', self._mock_server_info_get)

        si = server_info.ServerInfo(common.SESSION_KEY)
        assert si.is_shc_member()

    def test_get_shc_members(self, monkeypatch):
        monkeypatch.setattr(binding.Context, 'get', self._mock_server_info_get)

        si = server_info.ServerInfo(common.SESSION_KEY)
        assert si.get_shc_members() == [('SHC01_SearchHead02_1_85', 'https://192.168.1.85:8089'),
                                        ('SHC01_SearchHead03_1_86', 'https://192.168.1.86:8089'),
                                        ('SHC01_SearchHead01_1_84', u'https://192.168.1.84:8089')]

    def test_version(self, monkeypatch):
        monkeypatch.setattr(binding.Context, 'get', self._mock_server_info_get)

        si = server_info.ServerInfo(common.SESSION_KEY)
        assert si.version() == '6.3.1511.2'
