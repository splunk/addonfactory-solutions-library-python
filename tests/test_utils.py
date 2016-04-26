import sys
import os
import signal
import datetime
import pytest
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import utils


def test_handle_teardown_signals(monkeypatch):
    test_handle_teardown_signals.should_teardown = False

    def sig_handler(signum, frame):
        test_handle_teardown_signals.should_teardown = True

    utils.handle_teardown_signals(sig_handler)
    os.kill(os.getpid(), signal.SIGINT)
    assert test_handle_teardown_signals.should_teardown


def test_datatime_to_seconds(monkeypatch):
    total_seconds = 1456755646.0
    dt = datetime.datetime(2016, 2, 29, 14, 20, 46, 0)
    assert total_seconds == utils.datetime_to_seconds(dt)


def test_is_false(monkeypatch):
    for val in ('0', 'FALSE', 'F', 'N', 'NO', 'NONE', '', None):
        assert utils.is_false(val)

    for val in ('1', 'TRUE', 'T', 'Y', 'YES'):
        assert not utils.is_false(val)

    for val in ('00', 'FF', 'NN', 'NONO', '434324'):
        assert not utils.is_false(val)


def test_is_true(monkeypatch):
    for val in ('1', 'TRUE', 'T', 'Y', 'YES'):
        assert utils.is_true(val)

    for val in ('0', 'FALSE', 'F', 'N', 'NO', 'NONE', '', None):
        assert not utils.is_true(val)

    for val in ('00', 'FF', 'NN', 'NONO', '434324'):
        assert not utils.is_true(val)


def test_escape_json_control_chars(monkeypatch):
    str1 = r'hello\nworld'
    escaped_str1 = r'hello\\nworld'
    assert escaped_str1 == utils.escape_json_control_chars(str1)

    str1 = r'hello\rworld'
    escaped_str1 = r'hello\\rworld'
    assert escaped_str1 == utils.escape_json_control_chars(str1)

    str1 = r'hello\r\nworld'
    escaped_str1 = r'hello\\r\\nworld'
    assert escaped_str1 == utils.escape_json_control_chars(str1)


def test_retry(monkeypatch):
    def _old_func():
        raise ValueError('Exception for test.')

    _new_func = utils.retry(retries=1)(_old_func)
    with pytest.raises(ValueError):
        _new_func()
