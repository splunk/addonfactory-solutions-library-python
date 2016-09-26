import sys
import os.path as op

from splunklib import binding

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib.modular_input import ClassicEventWriter
from solnlib.modular_input import HECEventWriter
from solnlib.modular_input import create_hec_writer_from_input
from solnlib.modular_input import create_hec_writer_from_token_with_session_key
from solnlib.modular_input import create_hec_writer_from_token


def test_classic_event_writer(monkeypatch):
    class MockStdout(object):
        def __init__(self):
            self._buf = ''

        def read(self, size=None):
            content = self._buf
            self._buf = ''
            return content

        def write(self, event):
            self._buf += event

        def flush(self):
            pass

    mock_stdout = MockStdout()
    monkeypatch.setattr(sys, 'stdout', mock_stdout)

    ew = ClassicEventWriter()
    events = []
    events.append(ew.create_event(data='This is a test data1.',
                                  time=1372274622.493,
                                  index='main',
                                  host='localhost',
                                  source='Splunk',
                                  sourcetype='misc',
                                  stanza='test_scheme://test',
                                  unbroken=True,
                                  done=False))
    events.append(ew.create_event(data='This is a test data2.',
                                  time=1372274622.493,
                                  index='main',
                                  host='localhost',
                                  source='Splunk',
                                  sourcetype='misc',
                                  stanza='test_scheme://test',
                                  unbroken=True,
                                  done=True))
    ew.write_events(events)

    assert mock_stdout.read() == '<stream><event stanza="test_scheme://test" unbroken="1"><time>1372274622.493</time><index>main</index><host>localhost</host><source>Splunk</source><sourcetype>misc</sourcetype><data>This is a test data1.</data></event><event stanza="test_scheme://test" unbroken="1"><time>1372274622.493</time><index>main</index><host>localhost</host><source>Splunk</source><sourcetype>misc</sourcetype><data>This is a test data2.</data><done /></event></stream>'


def test_hec_event_writer(monkeypatch):
    def mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
        if path_segment.endswith('/http'):
            return common.make_response_record('{"entry": [{"content": {"port": 8088}}]}')
        else:
            return common.make_response_record('{"entry": [{"content": {"token": "87de04d1-0823-11e6-9c94-a45e60e34295"}}]}')

    def mock_post(self, path_segment, owner=None, app=None, sharing=None, headers=None, **query):
        assert query['body'] == '{"index": "main", "sourcetype": "misc", "source": "Splunk", "host": "localhost", "time": 1372274622.493, "event": "This is a test data1."}\n{"index": "main", "sourcetype": "misc", "source": "Splunk", "host": "localhost", "time": 1372274622.493, "event": "This is a test data2."}'

    def mock_get_hec_config(self, hec_input_name, session_key, scheme, host, port, **context):
        return "8088", "87de04d1-0823-11e6-9c94-a45e60e"

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.Context, 'get', mock_get)
    monkeypatch.setattr(binding.Context, 'post', mock_post)
    monkeypatch.setattr(HECEventWriter, '_get_hec_config', mock_get_hec_config)

    for i in range(4):
        ew = create_hec_event_writer(i)

        events = []
        events.append(ew.create_event(data='This is a test data1.',
                                      time=1372274622.493,
                                      index='main',
                                      host='localhost',
                                      source='Splunk',
                                      sourcetype='misc',
                                      stanza='test_scheme://test',
                                      unbroken=True,
                                      done=False))
        events.append(ew.create_event(data='This is a test data2.',
                                      time=1372274622.493,
                                      index='main',
                                      host='localhost',
                                      source='Splunk',
                                      sourcetype='misc',
                                      stanza='test_scheme://test',
                                      unbroken=True,
                                      done=True))
        ew.write_events(events)


def create_hec_event_writer(i):
    if i == 1:
        return create_hec_writer_from_input(
            'HECTestInput', 'https://localhost:8089', common.SESSION_KEY)
    elif i == 2:
        return create_hec_writer_from_token_with_session_key(
            'https://localhost:8089', common.SESSION_KEY,
            'https://localhost:8090', 'test_token')
    elif i == 3:
        return create_hec_writer_from_token(
            'https://localhost:8090', 'test_token')
    else:
        return HECEventWriter('HECTestInput', common.SESSION_KEY)
