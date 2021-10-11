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

import os.path as op
import socket
import sys

import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import net_utils


def test_resolve_hostname(monkeypatch):
    invalid_ip = "192.1.1"
    resolvable_ip = "192.168.0.1"
    unresolvable_ip1 = "192.168.1.1"
    unresolvable_ip2 = "192.168.1.2"
    unresolvable_ip3 = "192.168.1.3"

    def mock_gethostbyaddr(addr):
        if addr == resolvable_ip:
            return ("unittestServer", None, None)
        elif addr == unresolvable_ip1:
            raise socket.gaierror()
        elif addr == unresolvable_ip2:
            raise socket.herror()
        else:
            raise socket.timeout()

    monkeypatch.setattr(socket, "gethostbyaddr", mock_gethostbyaddr)

    with pytest.raises(ValueError):
        net_utils.resolve_hostname(invalid_ip)
    assert net_utils.resolve_hostname(resolvable_ip)
    assert net_utils.resolve_hostname(unresolvable_ip1) is None
    assert net_utils.resolve_hostname(unresolvable_ip2) is None
    assert net_utils.resolve_hostname(unresolvable_ip3) is None


def test_is_valid_hostname():
    assert net_utils.is_valid_hostname("splunk")
    assert net_utils.is_valid_hostname("splunk.com")
    assert net_utils.is_valid_hostname("localhost")
    assert not net_utils.is_valid_hostname("")
    assert not net_utils.is_valid_hostname("localhost:8000")
    assert not net_utils.is_valid_hostname("http://localhost:8000")


def test_is_valid_port():
    assert not net_utils.is_valid_port(0)
    assert not net_utils.is_valid_port("0")
    assert net_utils.is_valid_port("1")
    assert net_utils.is_valid_port(1)
    assert net_utils.is_valid_port(8080)
    assert net_utils.is_valid_port("8080")
    assert net_utils.is_valid_port("0808")
    assert net_utils.is_valid_port("65535")
    assert net_utils.is_valid_port(65535)
    assert not net_utils.is_valid_port("65536")
    assert not net_utils.is_valid_port(65536)


def test_is_valid_scheme():
    assert net_utils.is_valid_scheme("http")
    assert net_utils.is_valid_scheme("https")
    assert net_utils.is_valid_scheme("HTTP")
    assert net_utils.is_valid_scheme("HTTPS")
    assert net_utils.is_valid_scheme("HTTp")
    assert not net_utils.is_valid_scheme("non-http")


def test_check_css_params():
    @net_utils.check_css_params(
        a1=lambda x: x > 0,
        a2=lambda x: x is not None,
        a3=lambda x: x is None,
        a4=lambda x: x % 2 == 0,
    )
    def test_func(a1, a2=None, *args, **kwargs):
        pass

    with pytest.raises(ValueError):
        test_func(0)
    test_func(1)
    test_func(1, None)
    test_func(1, 2)
    test_func(1, 100, None, 1)
    with pytest.raises(ValueError):
        test_func(1, 100, a3=1)
    test_func(1, 100, a3=None)
    with pytest.raises(ValueError):
        test_func(1, 100, a3=None, a4=1)
    test_func(1, 100, a3=None, a4=2)
