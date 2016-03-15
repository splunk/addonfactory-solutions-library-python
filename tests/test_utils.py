import sys
import os
import signal
import datetime
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.common import utils


def test_handle_tear_down_signals():
    test_handle_tear_down_signals.should_tear_down = False

    def sig_handler(signum, frame):
        test_handle_tear_down_signals.should_tear_down = True

    utils.handle_tear_down_signals(sig_handler)
    os.kill(os.getpid(), signal.SIGINT)
    assert test_handle_tear_down_signals.should_tear_down


def test_datatime_to_seconds():
    total_seconds = 1456755646.0
    dt = datetime.datetime(2016, 2, 29, 14, 20, 46, 0)
    assert total_seconds == utils.datetime_to_seconds(dt)


def test_is_false():
    for val in ('0', 'FALSE', 'F', 'N', 'NO', 'NONE', '', None):
        assert utils.is_false(val)

    for val in ('1', 'TRUE', 'T', 'Y', 'YES'):
        assert not utils.is_false(val)

    for val in ('00', 'FF', 'NN', 'NONO', '434324'):
        assert not utils.is_false(val)


def test_is_true():
    for val in ('1', 'TRUE', 'T', 'Y', 'YES'):
        assert utils.is_true(val)

    for val in ('0', 'FALSE', 'F', 'N', 'NO', 'NONE', '', None):
        assert not utils.is_true(val)

    for val in ('00', 'FF', 'NN', 'NONO', '434324'):
        assert not utils.is_true(val)


def test_escape_json_control_chars():
    str1 = r'hello\nworld'
    escaped_str1 = r'hello\\nworld'
    assert escaped_str1 == utils.escape_json_control_chars(str1)

    str1 = r'hello\rworld'
    escaped_str1 = r'hello\\rworld'
    assert escaped_str1 == utils.escape_json_control_chars(str1)

    str1 = r'hello\r\nworld'
    escaped_str1 = r'hello\\r\\nworld'
    assert escaped_str1 == utils.escape_json_control_chars(str1)
