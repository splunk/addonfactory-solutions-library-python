# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

import datetime
import os.path as op
import sys

import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import context

from solnlib import credentials, time_parser


def test_time_parser():
    session_key = credentials.get_session_key(
        context.username,
        context.password,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )

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
