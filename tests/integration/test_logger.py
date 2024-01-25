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


def test_CVE_2023_32712():
    # CVE-2023-32712
    session_key = context.get_session_key()

    msg_prefix = "ASCII Table in one string: "
    time.sleep(30)
    search_results = search(session_key, f'search index=_internal "{msg_prefix}"')
    assert len(search_results) >= 1
    _raw_event = search_results[0]["_raw"]

    # test for nonwhite characters and white characters as they should be represented in fixed Splunk instance
    assert r"\x00" in _raw_event
    assert r"\x01\x02\x03\x04\x05\x06\x07\x08" in _raw_event
    # assert "\t\n" in _raw_event
    assert r"\x0b\x0c" in _raw_event
    # assert "\r" in _raw_event
    assert (
        r"\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f"
        in _raw_event
    )
    assert (
        " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
        in _raw_event
    )
    assert r"\x7f" in _raw_event

    # test for white characters as they shouldn't be represented in fixed Splunk instance
    def gen_ascii_chars_range(start: int = 0, stop: int = 128) -> str:
        chars_str = ""
        for i in range(start, stop):
            chars_str += chr(i)
        return chars_str

    ascii_chars_range_00_09 = gen_ascii_chars_range(start=0, stop=9)
    ascii_chars_range_0b_0d = gen_ascii_chars_range(start=11, stop=13)
    ascii_chars_range_0e_20 = gen_ascii_chars_range(start=14, stop=32)
    assert ascii_chars_range_00_09 not in _raw_event
    assert ascii_chars_range_0b_0d not in _raw_event
    assert ascii_chars_range_0e_20 not in _raw_event
