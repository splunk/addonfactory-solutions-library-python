import sys
import os.path as op
import unittest as ut
import socket

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.common import net_utils


class TestUtils(ut.TestCase):

    def test_resolve_hostname(self):
        invalid_ip = '192.1.1'
        resolvable_ip = '192.168.0.1'
        unresolvable_ip1 = '192.168.1.1'
        unresolvable_ip2 = '192.168.1.2'
        unresolvable_ip3 = '192.168.1.3'

        def _mock_gethostbyaddr(addr):
            if addr == resolvable_ip:
                return ("hostname", None, None)
            elif addr == unresolvable_ip1:
                raise socket.gaierror()
            elif addr == unresolvable_ip2:
                raise socket.herror()
            else:
                raise socket.timeout()

        # Save origin gethostbyaddr
        gethostbyaddr_backup = socket.gethostbyaddr
        socket.gethostbyaddr = _mock_gethostbyaddr

        with self.assertRaises(ValueError):
            net_utils.resolve_hostname(invalid_ip)
        self.assertIsNotNone(net_utils.resolve_hostname(resolvable_ip))
        self.assertIsNone(net_utils.resolve_hostname(unresolvable_ip1))
        self.assertIsNone(net_utils.resolve_hostname(unresolvable_ip2))
        self.assertIsNone(net_utils.resolve_hostname(unresolvable_ip3))

        # Restore gethostbyaddr
        socket.gethostbyaddr = gethostbyaddr_backup

if __name__ == '__main__':
    ut.main(verbosity=2)
