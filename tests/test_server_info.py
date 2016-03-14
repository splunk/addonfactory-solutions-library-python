import sys
import os.path as op
import unittest as ut

import rest_client

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import server_info


class TestServerInfo(ut.TestCase):

    def setUp(self):
        rest_client.setup_server_info_env()

    def tearDown(self):
        rest_client.restore_server_info_env()

    def test_is_captain(self):
        si = server_info.ServerInfo(rest_client.SESSION_KEY)
        self.assertTrue(si.is_captain())

    def test_is_cloud_instance(self):
        si = server_info.ServerInfo(rest_client.SESSION_KEY)
        self.assertFalse(si.is_cloud_instance())

    def test_is_search_head(self):
        si = server_info.ServerInfo(rest_client.SESSION_KEY)
        self.assertTrue(si.is_search_head())

    def test_is_shc_member(self):
        si = server_info.ServerInfo(rest_client.SESSION_KEY)
        self.assertTrue(si.is_shc_member())

    def test_get_shc_members(self):
        si = server_info.ServerInfo(rest_client.SESSION_KEY)
        self.assertEqual(si.get_shc_members(),
                         [('SHC01_SearchHead02_1_85', 'https://192.168.1.85:8089'),
                          ('SHC01_SearchHead03_1_86', 'https://192.168.1.86:8089'),
                          ('SHC01_SearchHead01_1_84', u'https://192.168.1.84:8089')])

    def test_version(self):
        si = server_info.ServerInfo(rest_client.SESSION_KEY)
        self.assertEqual(si.version(), '6.3.1511.2')

if __name__ == '__main__':
    ut.main(verbosity=2)
