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

import context
import conftest
import datetime
import os.path as op
import sys
import pytest
from solnlib import time_parser

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))


def test_time_parser(monkeypatch):
    conftest.mock_splunk(monkeypatch)

    session_key = context.get_session_key()
    tp = time_parser.TimeParser(session_key)

    assert tp.to_seconds("2011-07-06T21:54:23.000-07:00") == 1310014463.0
    assert tp.to_utc("2011-07-06T21:54:23.000-07:00") == datetime.datetime(
        2011, 7, 7, 4, 54, 23
    )
    assert (
        tp.to_local("2011-07-06T21:54:23.000-07:00") == "2011-07-07T04:54:23.000+00:00"
    )

    with pytest.raises(time_parser.InvalidTimeFormatException):
        tp.to_seconds("2011-07-06T21:54:23.000-07;00")
    with pytest.raises(time_parser.InvalidTimeFormatException):
        tp.to_utc("2011-07-06T21:54:23.000-07;00")
    with pytest.raises(time_parser.InvalidTimeFormatException):
        tp.to_local("2011-07-06T21:54:23.000-07;00")
