# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

import sys
import os.path as op
import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import ip_math


def test_ip2long(monkeypatch):
    valid_ip = "192.168.1.1"
    invalid_ip1 = "192.168.1"
    invalid_ip2 = 192

    assert ip_math.ip2long(valid_ip) == 3232235777
    with pytest.raises(ValueError):
        ip_math.ip2long(invalid_ip1)
    with pytest.raises(ValueError):
        ip_math.ip2long(invalid_ip2)


def test_long2ip(monkeypatch):
    valid_ip = 3232235777
    invalid_ip1 = -1
    invalid_ip2 = pow(2, 32)
    invalid_ip3 = "192.168.1.1"

    assert ip_math.long2ip(valid_ip) == "192.168.1.1"
    with pytest.raises(ValueError):
        ip_math.long2ip(invalid_ip1)
    with pytest.raises(ValueError):
        ip_math.long2ip(invalid_ip2)
    with pytest.raises(ValueError):
        ip_math.long2ip(invalid_ip3)


def test_cidr2long(monkeypatch):
    valid_cidr = "192.168.1.0/24"
    invalid_cidr1 = "192.168.1.0/16"
    invalid_cidr2 = "192.168.1.0"
    invalid_cidr3 = 123

    assert ip_math.cidr2long(valid_cidr) == (3232235776, 3232236031)
    with pytest.raises(ValueError):
        ip_math.cidr2long(invalid_cidr1)
    with pytest.raises(ValueError):
        ip_math.cidr2long(invalid_cidr2)
    with pytest.raises(ValueError):
        ip_math.cidr2long(invalid_cidr3)


def test_is_valid_mac(monkeypatch):
    valid_mac = "2e:ef:19:25:dc:47"
    invalid_mac1 = "2e:ef:19:25:dc:47:39"
    invalid_mac2 = 123

    assert ip_math.is_valid_mac(valid_mac)
    assert not ip_math.is_valid_mac(invalid_mac1)
    assert not ip_math.is_valid_mac(invalid_mac2)


def test_is_valid_mask(monkeypatch):
    valid_mask = 24
    invalid_mask1 = -1
    invalid_mask2 = 33

    assert ip_math.is_valid_mask(valid_mask)
    assert not ip_math.is_valid_mask(invalid_mask1)
    assert not ip_math.is_valid_mask(invalid_mask2)


def test_is_valid_cidr(monkeypatch):
    valid_cidr = "192.168.1.0/24"
    invalid_cidr1 = "192.168.1.0/16"
    invalid_cidr2 = "192.168.1.0"
    invalid_cidr3 = 123

    assert ip_math.is_valid_cidr(valid_cidr)
    assert not ip_math.is_valid_cidr(invalid_cidr1)
    assert not ip_math.is_valid_cidr(invalid_cidr2)
    assert not ip_math.is_valid_cidr(invalid_cidr3)


def test_is_valid_ip(monkeypatch):
    valid_ip = "192.168.1.1"
    invalid_ip1 = "192.168.1"
    invalid_ip2 = 192

    assert ip_math.is_valid_ip(valid_ip)
    assert not ip_math.is_valid_ip(invalid_ip1)
    assert not ip_math.is_valid_ip(invalid_ip2)


def test_expand_ip_range_to_cidr(monkeypatch):
    # ('192.168.0.1', '192.168.44.128')
    valid_ip_range = (3232235521, 3232246912)
    invalid_ip_range1 = (3232246912, 3232235521)
    invalid_ip_range2 = (-1, 3232235521)
    invalid_ip_range3 = ("192.168.1.1", 3232235521)
    invalid_ip_range4 = ("192.168.1.1", "192.168.1.100")

    cidr = [
        "192.168.16.0/20",
        "192.168.8.0/21",
        "192.168.32.0/21",
        "192.168.4.0/22",
        "192.168.40.0/22",
        "192.168.2.0/23",
        "192.168.1.0/24",
        "192.168.0.128/25",
        "192.168.44.0/25",
        "192.168.0.64/26",
        "192.168.0.32/27",
        "192.168.0.16/28",
        "192.168.0.8/29",
        "192.168.0.4/30",
        "192.168.0.2/31",
        "192.168.0.1/32",
        "192.168.44.128/32",
    ]
    assert ip_math.expand_ip_range_to_cidr(valid_ip_range) == cidr

    with pytest.raises((ValueError, TypeError)):
        ip_math.expand_ip_range_to_cidr(invalid_ip_range1)
    with pytest.raises((ValueError, TypeError)):
        ip_math.expand_ip_range_to_cidr(invalid_ip_range2)
    with pytest.raises((ValueError, TypeError)):
        ip_math.expand_ip_range_to_cidr(invalid_ip_range3)
    with pytest.raises((ValueError, TypeError)):
        ip_math.expand_ip_range_to_cidr(invalid_ip_range4)
