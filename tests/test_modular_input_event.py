import sys
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib.modular_input import XMLEvent
from solnlib.modular_input import HECEvent


class TestXMLEvent(object):

    @classmethod
    def setup_class(cls):
        cls.xe1 = XMLEvent(data='This is a test data1.',
                           time=1372274622.493,
                           index='main',
                           host='localhost',
                           source='Splunk',
                           sourcetype='misc',
                           stanza='test_scheme://test',
                           unbroken=True,
                           done=False)

        cls.xe2 = XMLEvent(data='This is a test data2.',
                           time=1372274622.493,
                           index='main',
                           host='localhost',
                           source='Splunk',
                           sourcetype='misc',
                           stanza='test_scheme://test',
                           unbroken=True,
                           done=True)

        cls.xe3 = XMLEvent(data='This is a test data3.',
                           time=1372274622.493,
                           index='main',
                           host='localhost',
                           source='Splunk',
                           sourcetype='misc',
                           stanza='test_scheme://test')

        cls.xe4 = XMLEvent(data=u'This is a non utf-8 \u2603 data4.',
                           time=1372274622.493,
                           index='main',
                           host='localhost',
                           source='Splunk',
                           sourcetype='misc',
                           stanza='test_scheme://test')

    def test_str(self, monkeypatch):
        assert str(self.xe1) == '{"index": "main", "host": "localhost", "done": false, "source": "Splunk", "time": 1372274622.493, "data": "This is a test data1.", "stanza": "test_scheme://test", "unbroken": true, "sourcetype": "misc"}'
        assert str(self.xe2) == '{"index": "main", "host": "localhost", "done": true, "source": "Splunk", "time": 1372274622.493, "data": "This is a test data2.", "stanza": "test_scheme://test", "unbroken": true, "sourcetype": "misc"}'
        assert str(self.xe3) == '{"index": "main", "host": "localhost", "done": false, "source": "Splunk", "time": 1372274622.493, "data": "This is a test data3.", "stanza": "test_scheme://test", "unbroken": false, "sourcetype": "misc"}'

    def test_format_events(self, monkeypatch):
        assert XMLEvent.format_events([self.xe1, self.xe2]) == ['<stream><event stanza="test_scheme://test" unbroken="1"><time>1372274622.493</time><index>main</index><host>localhost</host><source>Splunk</source><sourcetype>misc</sourcetype><data>This is a test data1.</data></event><event stanza="test_scheme://test" unbroken="1"><time>1372274622.493</time><index>main</index><host>localhost</host><source>Splunk</source><sourcetype>misc</sourcetype><data>This is a test data2.</data><done /></event></stream>']
        assert XMLEvent.format_events([self.xe3]) == ['<stream><event stanza="test_scheme://test"><time>1372274622.493</time><index>main</index><host>localhost</host><source>Splunk</source><sourcetype>misc</sourcetype><data>This is a test data3.</data></event></stream>']
        assert XMLEvent.format_events([self.xe4]) == ['<stream><event stanza="test_scheme://test"><time>1372274622.493</time><index>main</index><host>localhost</host><source>Splunk</source><sourcetype>misc</sourcetype><data>This is a non utf-8 \xe2\x98\x83 data4.</data></event></stream>']


class TestHECEvent(object):

    @classmethod
    def setup_class(cls):
        cls.he1 = HECEvent(data='This is a test data1.',
                           time=1372274622.493,
                           index='main',
                           host='localhost',
                           source='Splunk',
                           sourcetype='misc',
                           stanza='test_scheme://test',
                           unbroken=True,
                           done=False)

        cls.he2 = HECEvent(data='This is a test data2.',
                           time=1372274622.493,
                           index='main',
                           host='localhost',
                           source='Splunk',
                           sourcetype='misc',
                           stanza='test_scheme://test',
                           unbroken=True,
                           done=True)

        cls.he3 = HECEvent(data='This is a test data3.',
                           time=1372274622.493,
                           index='main',
                           host='localhost',
                           source='Splunk',
                           sourcetype='misc',
                           stanza='test_scheme://test')

    def test_str(self, monkeypatch):
        assert str(self.he1) == '{"index": "main", "host": "localhost", "done": false, "source": "Splunk", "time": 1372274622.493, "data": "This is a test data1.", "stanza": "test_scheme://test", "unbroken": true, "sourcetype": "misc"}'
        assert str(self.he2) == '{"index": "main", "host": "localhost", "done": true, "source": "Splunk", "time": 1372274622.493, "data": "This is a test data2.", "stanza": "test_scheme://test", "unbroken": true, "sourcetype": "misc"}'
        assert str(self.he3) == '{"index": "main", "host": "localhost", "done": false, "source": "Splunk", "time": 1372274622.493, "data": "This is a test data3.", "stanza": "test_scheme://test", "unbroken": false, "sourcetype": "misc"}'

    def test_format_events(self, monkeypatch):
        assert HECEvent.format_events([self.he1, self.he2]) == ['{"index": "main", "sourcetype": "misc", "source": "Splunk", "host": "localhost", "time": 1372274622.493, "event": "This is a test data1."}\n{"index": "main", "sourcetype": "misc", "source": "Splunk", "host": "localhost", "time": 1372274622.493, "event": "This is a test data2."}']
        assert HECEvent.format_events([self.he3]) == ['{"index": "main", "sourcetype": "misc", "source": "Splunk", "host": "localhost", "time": 1372274622.493, "event": "This is a test data3."}']
