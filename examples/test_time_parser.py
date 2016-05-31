import sys
import datetime
import pytest
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import credentials
from solnlib import time_parser
import context


def test_time_parser():
    session_key = credentials.get_session_key(
        context.username, context.password, scheme=context.scheme,
        host=context.host, port=context.port)

    tp = time_parser.TimeParser(session_key)

    assert tp.to_seconds('2011-07-06T21:54:23.000-07:00') == 1310014463.0
    assert tp.to_utc('2011-07-06T21:54:23.000-07:00') == \
        datetime.datetime(2011, 7, 7, 4, 54, 23)
    assert tp.to_local('2011-07-06T21:54:23.000-07:00') == \
        '2011-07-07T12:54:23.000+08:00'

    with pytest.raises(time_parser.InvalidTimeFormatException):
        tp.to_seconds('2011-07-06T21:54:23.000-07;00')
    with pytest.raises(time_parser.InvalidTimeFormatException):
        tp.to_utc('2011-07-06T21:54:23.000-07;00')
    with pytest.raises(time_parser.InvalidTimeFormatException):
        tp.to_local('2011-07-06T21:54:23.000-07;00')
