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
import unittest

import context

from solnlib import server_info


class ServerInfoTest(unittest.TestCase):
    def test_methods(self):
        # This test does not check for guid, version and SHC related methods.
        session_key = context.get_session_key()
        si = server_info.ServerInfo(
            session_key, context.scheme, context.host, context.port
        )
        self.assertEqual("custom-servername", si.server_name)
        self.assertFalse(si.is_search_head())
        self.assertFalse(si.is_shc_member())
        with self.assertRaises(server_info.ServerInfoException):
            si.get_shc_members()
        with self.assertRaises(server_info.ServerInfoException):
            si.captain_info()
        with self.assertRaises(server_info.ServerInfoException):
            si.is_captain_ready()
        self.assertFalse(si.is_captain())
        self.assertFalse(si.is_cloud_instance())
