# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

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
