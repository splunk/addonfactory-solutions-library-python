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

import os
import os.path as op
import sys

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import splunkenv


def test_splunkenv():
    assert "SPLUNK_HOME" in os.environ

    splunkhome_path = splunkenv.make_splunkhome_path(["etc", "apps"])
    assert splunkhome_path == op.join(os.environ["SPLUNK_HOME"], "etc", "apps")

    server_name, host_name = splunkenv.get_splunk_host_info()
    assert server_name
    assert host_name

    splunk_bin = splunkenv.get_splunk_bin()
    assert splunk_bin in [
        op.join(os.environ["SPLUNK_HOME"], "bin", "splunk"),
        op.join(os.environ["SPLUNK_HOME"], "bin", "splunk.exe"),
    ]

    scheme, host, port = splunkenv.get_splunkd_access_info()
    assert scheme
    assert host
    assert port

    uri = splunkenv.get_splunkd_uri()
    assert uri == f"{scheme}://{host}:{port}"
