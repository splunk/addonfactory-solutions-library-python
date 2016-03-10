import sys
import os
import signal
import datetime
import os.path as op
import unittest as ut

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.common import utils

should_tear_down = False


def sig_handler(signum, frame):
    global should_tear_down
    should_tear_down = True


class TestUtils(ut.TestCase):

    def test_handle_tear_down_signals(self):
        utils.handle_tear_down_signals(sig_handler)
        os.kill(os.getpid(), signal.SIGINT)
        self.assertTrue(should_tear_down)

    def test_datatime_to_seconds(self):
        total_seconds = 1456755646.0
        dt = datetime.datetime(2016, 2, 29, 14, 20, 46, 0)
        self.assertTrue(total_seconds == utils.datetime_to_seconds(dt))

    def test_is_false(self):
        for val in ('0', 'FALSE', 'F', 'N', 'NO', 'NONE', '', None):
            self.assertTrue(utils.is_false(val))

        for val in ('1', 'TRUE', 'T', 'Y', 'YES'):
            self.assertFalse(utils.is_false(val))

        for val in ('00', 'FF', 'NN', 'NONO', '434324'):
            self.assertFalse(utils.is_false(val))

    def test_is_true(self):
        for val in ('0', 'FALSE', 'F', 'N', 'NO', 'NONE', '', None):
            self.assertFalse(utils.is_true(val))

        for val in ('1', 'TRUE', 'T', 'Y', 'YES'):
            self.assertTrue(utils.is_true(val))

        for val in ('00', 'FF', 'NN', 'NONO', '434324'):
            self.assertFalse(utils.is_true(val))

    def test_escape_json_control_chars(self):
        str1 = r'hello\nworld'
        escaped_str1 = r'hello\\nworld'
        self.assertTrue(escaped_str1 ==
                        utils.escape_json_control_chars(str1))

        str1 = r'hello\rworld'
        escaped_str1 = r'hello\\rworld'
        self.assertTrue(escaped_str1 ==
                        utils.escape_json_control_chars(str1))

        str1 = r'hello\r\nworld'
        escaped_str1 = r'hello\\r\\nworld'
        self.assertTrue(escaped_str1 ==
                        utils.escape_json_control_chars(str1))

if __name__ == '__main__':
    ut.main(verbosity=2)
