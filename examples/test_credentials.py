import sys
import os.path as op
import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import credentials
import context


def test_credential_manager():
    session_key = credentials.get_session_key(
        context.username, context.password, scheme=context.scheme,
        host=context.host, port=context.port)

    cm = credentials.CredentialManager(session_key, context.app, owner=context.owner,
                                       realm=context.app, scheme=context.scheme,
                                       host=context.host, port=context.port)

    cm.set_password('testuser1', 'password1')
    assert cm.get_password('testuser1') == 'password1'

    long_password = ''.join(['1111111111' for i in xrange(30)])
    cm.set_password('testuser2', long_password)
    assert cm.get_password('testuser2') == long_password

    cm.delete_password('testuser1')
    with pytest.raises(credentials.CredentialNotExistException):
        cm.get_password('testuser1')

    cm.delete_password('testuser2')
    with pytest.raises(credentials.CredentialNotExistException):
        cm.get_password('testuser2')
