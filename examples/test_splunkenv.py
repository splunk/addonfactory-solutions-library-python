# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

import sys
import os
import os.path as op

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
    assert uri == "{scheme}://{host}:{port}".format(scheme=scheme, host=host, port=port)
