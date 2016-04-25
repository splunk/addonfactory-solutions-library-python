import sys
import os.path as op
import socket
import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import net_utils


def test_resolve_hostname(monkeypatch):
    invalid_ip = '192.1.1'
    resolvable_ip = '192.168.0.1'
    unresolvable_ip1 = '192.168.1.1'
    unresolvable_ip2 = '192.168.1.2'
    unresolvable_ip3 = '192.168.1.3'

    def _mock_gethostbyaddr(addr):
        if addr == resolvable_ip:
            return ('unittestServer', None, None)
        elif addr == unresolvable_ip1:
            raise socket.gaierror()
        elif addr == unresolvable_ip2:
            raise socket.herror()
        else:
            raise socket.timeout()

    monkeypatch.setattr(socket, 'gethostbyaddr', _mock_gethostbyaddr)

    with pytest.raises(ValueError):
        net_utils.resolve_hostname(invalid_ip)
    assert net_utils.resolve_hostname(resolvable_ip)
    assert net_utils.resolve_hostname(unresolvable_ip1) is None
    assert net_utils.resolve_hostname(unresolvable_ip2) is None
    assert net_utils.resolve_hostname(unresolvable_ip3) is None
