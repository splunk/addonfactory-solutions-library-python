# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

import os.path as op
import sys

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import context

from solnlib import credentials, hec_config


def test_hec_config():
    session_key = credentials.get_session_key(
        context.username,
        context.password,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )
    config = hec_config.HECConfig(session_key)
    stanza = {
        "index": "main",
        "sourcetype": "akamai:cm:json2",
        "token": "A0-5800-406B-9224-8E1DC4E720B7",
    }

    assert config.delete_input("not_exists") is None
    name = "hec_config_testing"
    config.delete_input(name)
    assert config.get_input(name) is None

    config.create_input(name, stanza)
    res = config.get_input(name)
    for k in ["index", "sourcetype", "token"]:
        assert res[k] == stanza[k]

    config.delete_input(name)
    assert config.get_input(name) is None

    setting = {
        "enableSSL": "1",
        "disabled": "1",
        "useDeploymentServer": "0",
        "port": "8087",
        "output_mode": "json",
    }

    config.update_settings(setting)
    new_settings = config.get_settings()
    for k in ["enableSSL", "disabled", "useDeploymentServer", "port"]:
        assert new_settings[k] == setting[k]

    limits = {"max_content_length": "4000000"}

    config.set_limits(limits)
    new_limits = config.get_limits()
    assert new_limits["max_content_length"] == limits["max_content_length"]


if __name__ == "__main__":
    test_hec_config()
