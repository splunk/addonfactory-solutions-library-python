import sys
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))

import context
from solnlib import credentials
from solnlib.modular_input import event_writer as hew


def test_hec_event_writer():
    session_key = credentials.get_session_key(
        context.username, context.password, scheme=context.scheme,
        host=context.host, port=context.port)

    ew = hew.HECEventWriter("test", session_key)
    m = {}
    for i in xrange(1000):
        m[i] = "i lover you"
    e = ew.create_event(m, index="main",
                        host="testing", sourcetype="hec")
    ew.write_events([e])


if __name__ == "__main__":
    test_hec_event_writer()
