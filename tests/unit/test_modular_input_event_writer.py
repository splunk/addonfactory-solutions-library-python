#
# Copyright 2023 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
import sys

import common
import pytest
from splunklib import binding
from unittest.mock import patch

from solnlib.modular_input import ClassicEventWriter, HECEventWriter
from solnlib.modular_input.event_writer import FunctionDeprecated, deprecation_msg


def test_classic_event_writer(monkeypatch):
    class MockStdout:
        def __init__(self):
            self._buf = ""
            self.write_count = 0

        def read(self, size=None):
            content = self._buf
            self._buf = ""
            return content

        def write(self, event):
            self._buf += event
            self.write_count += 1

        def flush(self):
            pass

    mock_stdout = MockStdout()
    monkeypatch.setattr(sys, "stdout", mock_stdout)

    ew = ClassicEventWriter()
    events = []
    events.append(
        ew.create_event(
            data="This is a test data1.",
            time=1372274622.493,
            index="main",
            host="localhost",
            source="Splunk",
            sourcetype="misc",
            stanza="test_scheme://test",
            unbroken=True,
            done=False,
        )
    )
    events.append(
        ew.create_event(
            data="This is a test data2.",
            time=1372274622.493,
            index="main",
            host="localhost",
            source="Splunk",
            sourcetype="misc",
            stanza="test_scheme://test",
            unbroken=True,
            done=True,
        )
    )
    ew.write_events(events)

    assert (
        mock_stdout.read()
        == '<stream><event stanza="test_scheme://test" unbroken="1"><time>1372274622.493</time><index>main'
        "</index><host>localhost</host><source>Splunk</source><sourcetype>misc</sourcetype><data>"
        'This is a test data1.</data></event><event stanza="test_scheme://test" unbroken="1"><time>'
        "1372274622.493</time><index>main</index><host>localhost</host><source>Splunk</source><sourcetype>misc"
        "</sourcetype><data>This is a test data2.</data><done /></event></stream>"
    )
    assert mock_stdout.write_count == 1


def create_hec_event_writer__create_from_input(hec=False):
    return HECEventWriter.create_from_input(
        "HECTestInput",
        "https://localhost:8089",
        common.SESSION_KEY,
        global_settings_schema=hec,
    )


def create_hec_event_writer__create_from_token_with_session_key(hec=False):
    return HECEventWriter.create_from_token_with_session_key(
        "https://localhost:8089",
        common.SESSION_KEY,
        "https://localhost:8090",
        "test_token",
        global_settings_schema=hec,
    )


def create_hec_event_writer__create_from_token(hec=False):
    return HECEventWriter.create_from_token(
        "https://localhost:8090", "test_token", global_settings_schema=hec
    )


def create_hec_event_writer__create_from_token__external_host(hec=False):
    return HECEventWriter.create_from_token(
        "https://external:8090", "test_token", global_settings_schema=hec
    )


def create_hec_event_writer__constructor(hec=False):
    return HECEventWriter(
        "HECTestInput", common.SESSION_KEY, global_settings_schema=hec
    )


@pytest.mark.parametrize(
    "create_hec_event_writer, has_splunk_home",
    [
        (create_hec_event_writer__constructor, True),
        (create_hec_event_writer__create_from_input, True),
        (create_hec_event_writer__create_from_token_with_session_key, True),
        (create_hec_event_writer__create_from_token, True),
        (create_hec_event_writer__create_from_token__external_host, False),
    ],
)
def test_hec_event_writer(monkeypatch, create_hec_event_writer, has_splunk_home):
    def mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
        if path_segment.endswith("/http"):
            return common.make_response_record(
                '{"entry": [{"content": {"port": 8088}}]}'
            )
        else:
            return common.make_response_record(
                '{"entry": [{"content": {"token": "87de04d1-0823-11e6-9c94-a45e60e34295"}}]}'
            )

    def mock_post(
        self, path_segment, owner=None, app=None, sharing=None, headers=None, **query
    ):
        event_strings = [
            json.dumps(json.loads(e), sort_keys=True)
            for e in query["body"].decode("utf-8").split("\n")
        ]

        assert (
            event_strings[0]
            == '{"event": "This is a test data1.", "host": "localhost", "index": "main", '
            '"source": "Splunk", "sourcetype": "misc", "time": 1372274622.493}'
        )
        assert (
            event_strings[1]
            == '{"event": "This is a test data2.", "host": "localhost", "index": "main", '
            '"source": "Splunk", "sourcetype": "misc", "time": 1372274622.493}'
        )

    def mock_get_hec_config(
        self, hec_input_name, session_key, scheme, host, port, **context
    ):
        return "8088", "87de04d1-0823-11e6-9c94-a45e60e"

    if has_splunk_home:
        common.mock_splunkhome(monkeypatch)
    else:
        # simulate an environment that has no splunk installation
        monkeypatch.delenv("SPLUNK_HOME", raising=False)
        monkeypatch.delenv("SPLUNK_ETC", raising=False)
    monkeypatch.setattr(binding.Context, "get", mock_get)
    monkeypatch.setattr(binding.Context, "post", mock_post)
    monkeypatch.setattr(HECEventWriter, "_get_hec_config", mock_get_hec_config)

    ew = create_hec_event_writer(hec=False)

    events = []
    events.append(
        ew.create_event(
            data="This is a test data1.",
            time=1372274622.493,
            index="main",
            host="localhost",
            source="Splunk",
            sourcetype="misc",
            stanza="test_scheme://test",
            unbroken=True,
            done=False,
        )
    )
    events.append(
        ew.create_event(
            data="This is a test data2.",
            time=1372274622.493,
            index="main",
            host="localhost",
            source="Splunk",
            sourcetype="misc",
            stanza="test_scheme://test",
            unbroken=True,
            done=True,
        )
    )
    ew.write_events(events)

    # length of this list will indicate how many times post was called
    times_post_called = []

    def mock_post_2(
        self, path_segment, owner=None, app=None, sharing=None, headers=None, **query
    ):
        times_post_called.append(1)

    monkeypatch.setattr(binding.Context, "post", mock_post_2)

    # test that there are 2 event batches created for write_event and post is called 2 times
    # max batch size is 1,000,000. If the max size is exceeded then a new batch is created.
    assert len(times_post_called) == 0

    events = []

    # each event length will be ~500 characters, 3000 events length will equal ~1,500,000 characters
    # which means there will be 2 event batches required when writing events via post

    events = []
    for i in range(3000):
        # length of this data_str is approximately 400 characters
        data_str = (
            "DATA"
            + str(i)
            + ": This is test data. This is test data. This is test data. This is test data. "
            "This is test data. This is test data. This is test data. This is test data. "
            "This is test data. This is test data. This is test data. This is test data. "
            "This is test data. This is test data. This is test data. This is test data. "
            "This is test data. This is test data. This is test data. "
            "This is test data. This is test data."
        )
        # total length of the events will be ~500 characters
        event = ew.create_event(
            data=data_str,
            time=1372274622.493,
            index="main",
            host="localhost",
            source="Splunk",
            sourcetype="misc",
            stanza="test_scheme://test",
            unbroken=True,
            done=True,
        )
        events.append(event)
    ew.write_events(events)

    # test that post is called 2 times
    assert len(times_post_called) == 2


@pytest.mark.parametrize(
    "create_hec_event_writer, hec, expected_scheme",
    [
        (create_hec_event_writer__constructor, True, "http"),
        (create_hec_event_writer__constructor, False, "https"),
        (create_hec_event_writer__create_from_input, True, "http"),
        (create_hec_event_writer__create_from_input, False, "https"),
        (create_hec_event_writer__create_from_token_with_session_key, True, "http"),
        (create_hec_event_writer__create_from_token_with_session_key, False, "https"),
        (create_hec_event_writer__create_from_token, False, "https"),
    ],
)
def test_hec_event_writer_gets_scheme_from_global_settings_if_requested(
    monkeypatch, create_hec_event_writer, hec, expected_scheme
):
    common.mock_splunkhome(monkeypatch)

    def mock_get_hec_config(
        self, hec_input_name, session_key, scheme, host, port, **context
    ):
        return "8088", "87de04d1-0823-11e6-9c94-a45e60e"

    monkeypatch.setattr(HECEventWriter, "_get_hec_config", mock_get_hec_config)

    ev = create_hec_event_writer(hec)
    assert ev._rest_client.scheme == expected_scheme


@patch("solnlib.splunkenv.use_btool")
@pytest.mark.parametrize(
    "create_hec_event_writer, hec, expected_scheme",
    [
        (create_hec_event_writer__constructor, True, "https"),
        (create_hec_event_writer__constructor, False, "http"),
        (create_hec_event_writer__create_from_input, True, "https"),
        (create_hec_event_writer__create_from_input, False, "https"),
        (create_hec_event_writer__create_from_token_with_session_key, True, "https"),
        (create_hec_event_writer__create_from_token_with_session_key, False, "https"),
        (create_hec_event_writer__create_from_token, False, "https"),
    ],
)
def test_hec_event_writer_gets_scheme_from_global_settings_if_requested_backdoor(
    mock_flag, monkeypatch, create_hec_event_writer, hec, expected_scheme
):
    mock_flag.return_value = True
    common.mock_splunkhome(monkeypatch)

    def mock_get_hec_config(
        self, hec_input_name, session_key, scheme, host, port, **context
    ):
        return "8088", "87de04d1-0823-11e6-9c94-a45e60e"

    monkeypatch.setattr(HECEventWriter, "_get_hec_config", mock_get_hec_config)

    ev = create_hec_event_writer(hec)
    assert ev._rest_client.scheme == expected_scheme


@pytest.mark.parametrize("hec", [False, True])
def test_hec_event_writer_create_from_token_deprecation(hec, monkeypatch, caplog):
    common.mock_splunkhome(monkeypatch)

    def mock_get_hec_config(
        self, hec_input_name, session_key, scheme, host, port, **context
    ):
        return "8088", "87de04d1-0823-11e6-9c94-a45e60e"

    monkeypatch.setattr(HECEventWriter, "_get_hec_config", mock_get_hec_config)

    if hec:
        with pytest.raises(FunctionDeprecated) as e:
            create_hec_event_writer__create_from_token(hec=True)
        assert e.value.args[0] == deprecation_msg
    else:
        with pytest.warns(DeprecationWarning, match=deprecation_msg):
            ev = create_hec_event_writer__create_from_token(hec=False)
            assert ev._rest_client.scheme == "https"
