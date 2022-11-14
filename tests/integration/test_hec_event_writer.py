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
import time

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import context
from _search import search

from solnlib.modular_input import event_writer as hew


def test_hec_event_writer():
    session_key = context.get_session_key()

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


def test_hec_event_writes_with_non_utf_8():
    # To test scenario listed in https://github.com/splunk/addonfactory-solutions-library-python/pull/112.
    test_name = "test_hec_event_writes_with_non_utf_8"
    session_key = context.get_session_key()
    ew = hew.HECEventWriter("test", session_key)
    event = ew.create_event(
        [
            {
                "test_name": test_name,
                "field_a": "Üü_Öö_Ää_some_text",
                "field_b": "some_text_Üü_Öö_Ää",
            },
        ],
        index="main",
        host="testing",
        sourcetype="hec",
    )
    ew.write_events([event])
    time.sleep(2)

    search_results = search(
        session_key, f"search index=main sourcetype=hec {test_name}"
    )

    assert len(search_results) == 1
    _raw_event = search_results[0]["_raw"]
    assert "Üü_Öö_Ää_some_text" in _raw_event
    assert "some_text_Üü_Öö_Ää" in _raw_event
    assert "\\u00dc\\u00fc_\\u00d6\\u00f6_\\u00c4\\u00e4_some_text" not in _raw_event
    assert "some_text_\\u00dc\\u00fc_\\u00d6\\u00f6_\\u00c4\\u00e4" not in _raw_event
