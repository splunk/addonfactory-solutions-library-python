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

from solnlib import credentials
from solnlib.modular_input import event_writer as hew


def test_hec_event_writer():
    session_key = credentials.get_session_key(
        context.username,
        context.password,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )

    ew = hew.HECEventWriter("test", session_key)
    m1 = {}
    for i in range(100):
        m1[i] = "test1 data %s" % i
    e1 = ew.create_event(m1, index="main", host="testing", sourcetype="hec")
    m2 = {}
    for i in range(100):
        m2[i] = "test2 data %s" % i
    e2 = ew.create_event(m2, index="main", host="testing", sourcetype="hec")
    ew.write_events([e1, e2])
