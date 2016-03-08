import sys
import os
import signal
import datetime
import os.path as op
import unittest as ut
import socket

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.common import utils as utils

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

    def test_is_valid_ip(self):
        valid_ip = '192.168.1.1'
        invalid_ip1 = '192.168.1'
        invalid_ip2 = 192

        self.assertTrue(utils.is_valid_ip(valid_ip))
        self.assertFalse(utils.is_valid_ip(invalid_ip1))
        self.assertFalse(utils.is_valid_ip(invalid_ip2))

    def test_resolve_hostname(self):
        invalid_ip = '192.1.1'
        resolvable_ip = '192.168.0.1'
        unresolvable_ip1 = '192.168.1.1'
        unresolvable_ip2 = '192.168.1.2'
        unresolvable_ip3 = '192.168.1.3'

        def mock_gethostbyaddr(addr):
            if addr == resolvable_ip:
                return ("hostname", None, None)
            elif addr == unresolvable_ip1:
                raise socket.gaierror()
            elif addr == unresolvable_ip2:
                raise socket.herror()
            else:
                raise socket.timeout()

        # Save origin gethostbyaddr
        old_gethostbyaddr = socket.gethostbyaddr
        socket.gethostbyaddr = mock_gethostbyaddr

        with self.assertRaises(ValueError):
            utils.resolve_hostname(invalid_ip)
        self.assertIsNotNone(utils.resolve_hostname(resolvable_ip))
        self.assertIsNone(utils.resolve_hostname(unresolvable_ip1))
        self.assertIsNone(utils.resolve_hostname(unresolvable_ip2))
        self.assertIsNone(utils.resolve_hostname(unresolvable_ip3))

        # Restore gethostbyaddr
        socket.gethostbyaddr = old_gethostbyaddr

if __name__ == '__main__':
    ut.main(verbosity=2)
