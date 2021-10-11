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
import datetime
import os.path as op
import sys

import common
import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunklib import binding

import solnlib.time_parser as stp


def test_time_parser(monkeypatch):
    mode = 0

    def mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
        if mode == 0:
            return common.make_response_record(
                '{"2011-07-06T21:54:23.000-07:00": "1310014463.0"}'
            )
        if mode == 1:
            return common.make_response_record(
                '{"2011-07-06T21:54:23.000-07:00": "2011-07-07T12:54:23.000+08:00"}'
            )
        else:
            raise binding.HTTPError(common.make_response_record("", status=400))

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.Context, "get", mock_get)

    tp = stp.TimeParser(common.SESSION_KEY)

    assert tp.to_seconds("2011-07-06T21:54:23.000-07:00") == 1310014463.0
    assert tp.to_utc("2011-07-06T21:54:23.000-07:00") == datetime.datetime(
        2011, 7, 7, 4, 54, 23
    )
    mode = 1
    assert (
        tp.to_local("2011-07-06T21:54:23.000-07:00") == "2011-07-07T12:54:23.000+08:00"
    )

    mode = 2
    with pytest.raises(stp.InvalidTimeFormatException):
        tp.to_seconds("2011-07-06T21:54:23.000-07;00")
    with pytest.raises(stp.InvalidTimeFormatException):
        tp.to_utc("2011-07-06T21:54:23.000-07;00")
    with pytest.raises(stp.InvalidTimeFormatException):
        tp.to_local("2011-07-06T21:54:23.000-07;00")
