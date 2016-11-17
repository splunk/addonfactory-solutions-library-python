import datetime
import os.path as op
import sys

import pytest

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import solnlib.time_parser as stp
from solnlib.packages.splunklib import binding


def test_time_parser(monkeypatch):
    mode = 0

    def mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
        if mode == 0:
            return common.make_response_record('{"2011-07-06T21:54:23.000-07:00": "1310014463.0"}')
        if mode == 1:
            return common.make_response_record('{"2011-07-06T21:54:23.000-07:00": "2011-07-07T12:54:23.000+08:00"}')
        else:
            raise binding.HTTPError(common.make_response_record('', status=400))

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.Context, 'get', mock_get)

    tp = stp.TimeParser(common.SESSION_KEY)

    assert tp.to_seconds('2011-07-06T21:54:23.000-07:00') == 1310014463.0
    assert tp.to_utc('2011-07-06T21:54:23.000-07:00') == \
        datetime.datetime(2011, 7, 7, 4, 54, 23)
    mode = 1
    assert tp.to_local('2011-07-06T21:54:23.000-07:00') == \
        '2011-07-07T12:54:23.000+08:00'

    mode = 2
    with pytest.raises(stp.InvalidTimeFormatException):
        tp.to_seconds('2011-07-06T21:54:23.000-07;00')
    with pytest.raises(stp.InvalidTimeFormatException):
        tp.to_utc('2011-07-06T21:54:23.000-07;00')
    with pytest.raises(stp.InvalidTimeFormatException):
        tp.to_local('2011-07-06T21:54:23.000-07;00')
