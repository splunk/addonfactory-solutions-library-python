import sys
import os.path as op
import pytest

from splunklib import client

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import solnlib.splunk_rest_client as rest_client
from solnlib import credentials
from solnlib import conf_manager
import context


def test_conf_manager():
    session_key = credentials.get_session_key(
        context.username, context.password, scheme=context.scheme,
        host=context.host, port=context.port)

    cfsm = rest_client.SplunkRestClient(
        session_key, context.app, owner=context.owner,
        scheme=context.scheme, host=context.host, port=context.port).confs
    try:
        cfsm.get('test')
    except client.HTTPError:
        cfsm.create('test')

    cfm = conf_manager.ConfManager(
        'test', session_key, context.app, owner=context.owner,
        scheme=context.scheme, host=context.host, port=context.port)
    cfm.update('test_stanza', {'k1': 1, 'k2': 2}, ['k1'])
    assert cfm.get('test_stanza')['k1'] == 1
    assert int(cfm.get('test_stanza')['k2']) == 2
    assert len(cfm.get_all()) == 1
    cfm.delete('test_stanza')
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        cfm.get('test_stanza')
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        cfm.delete('test_stanza')
    cfm.reload()
