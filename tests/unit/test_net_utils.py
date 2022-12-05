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

import socket

import pytest

from solnlib import net_utils


def test_resolve_hostname(monkeypatch):
    invalid_ip = "192.1.1"
    resolvable_ip = "192.168.0.1"
    unresolvable_ip1 = "192.168.1.1"
    unresolvable_ip2 = "192.168.1.2"
    unresolvable_ip3 = "192.168.1.3"

    def mock_gethostbyaddr(addr):
        if addr == resolvable_ip:
            return "unittestServer", None, None
        elif addr == unresolvable_ip1:
            raise socket.gaierror()
        elif addr == unresolvable_ip2:
            raise socket.herror()
        else:
            raise socket.timeout()

    monkeypatch.setattr(socket, "gethostbyaddr", mock_gethostbyaddr)

    with pytest.raises(ValueError):
        net_utils.resolve_hostname(invalid_ip)
    with pytest.raises(ValueError):
        assert net_utils.resolve_hostname(1234567)
    assert net_utils.resolve_hostname(resolvable_ip)
    assert net_utils.resolve_hostname(unresolvable_ip1) is None
    assert net_utils.resolve_hostname(unresolvable_ip2) is None
    assert net_utils.resolve_hostname(unresolvable_ip3) is None


@pytest.mark.parametrize(
    "hostname,expected_result",
    [
        ("splunk", True),
        ("splunk.", True),
        ("splunk.com", True),
        ("localhost", True),
        ("::1", True),
        ("", False),
        ("localhost:8000", False),
        ("http://localhost:8000", False),
        ("a" * 999, False),
    ],
)
def test_is_valid_hostname(hostname, expected_result):
    assert net_utils.is_valid_hostname(hostname) is expected_result


@pytest.mark.parametrize(
    "port,expected_result",
    [
        ("0.0", False),
        (0, False),
        ("0", False),
        ("65536", False),
        (65536, False),
        ("1", True),
        (1, True),
        (8080, True),
        ("8080", True),
        ("0808", True),
        ("65535", True),
        (65535, True),
    ],
)
def test_is_valid_port(port, expected_result):
    assert net_utils.is_valid_port(port) is expected_result


@pytest.mark.parametrize(
    "scheme,expected_result",
    [
        ("http", True),
        ("https", True),
        ("HTTP", True),
        ("HTTPS", True),
        ("HTTp", True),
        ("non-http", False),
    ],
)
def test_is_valid_scheme(scheme, expected_result):
    assert net_utils.is_valid_scheme(scheme) is expected_result


def test_validate_scheme_host_port():
    net_utils.validate_scheme_host_port("http", "localhost", 8080)
    net_utils.validate_scheme_host_port("https", "::1", 8089)
    with pytest.raises(ValueError):
        net_utils.validate_scheme_host_port("scheme", "localhost:8000", 8080)
    with pytest.raises(ValueError):
        net_utils.validate_scheme_host_port("http", "localhost:8000", 8080)
    with pytest.raises(ValueError):
        net_utils.validate_scheme_host_port("http", "localhost", 99999)
