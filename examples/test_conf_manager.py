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

    cfm = conf_manager.ConfManager(
        session_key, context.app, owner=context.owner,
        scheme=context.scheme, host=context.host, port=context.port)
    try:
        conf = cfm.get_conf('test')
    except conf_manager.ConfManagerException:
        conf = cfm.create_conf('test')
    conf.update('test_stanza', {'k1': 1, 'k2': 2}, ['k1'])
    assert conf.get('test_stanza')['k1'] == 1
    assert int(conf.get('test_stanza')['k2']) == 2
    assert len(conf.get_all()) == 1
    conf.delete('test_stanza')
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.get('test_stanza')
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.delete('test_stanza')
    conf.reload()
