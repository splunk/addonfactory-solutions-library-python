import sys
import hashlib
import os.path as op
import pytest

from splunklib import binding
from splunklib import client
from splunklib.data import record

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import credentials


def test_credential_manager(monkeypatch):
    credentials_store = {}

    def mock_storage_passwords_list(self, count=None, **kwargs):
        return credentials_store.values()

    def mock_storage_passwords_create(self, password, username, realm=None):
        title = '{}:{}:'.format(realm, username) if \
                realm else ':{}:'.format(username)
        password = client.StoragePassword(
            None,
            'storage/passwords/{}'.format(title),
            state=record(
                {'content': {'clear_password': password,
                             'encr_password': hashlib.md5(password).digest(),
                             'password': '********',
                             'realm': realm,
                             'username': username},
                 'title': title}))
        credentials_store[title] = password
        return password

    def mock_storage_passwords_delete(self, username, realm=None):
        title = '{}:{}:'.format(realm, username) \
                if realm else ':{}:'.format(username)
        if title in credentials_store:
            del credentials_store[title]
        else:
            raise KeyError('No such entity %s' % username)

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(
        client.StoragePasswords, 'list', mock_storage_passwords_list)
    monkeypatch.setattr(
        client.StoragePasswords, 'create', mock_storage_passwords_create)
    monkeypatch.setattr(
        client.StoragePasswords, 'delete', mock_storage_passwords_delete)

    cm = credentials.CredentialManager(
        common.SESSION_KEY, common.app, realm='realm_test')
    cm.set_password('testuser1', 'password1')
    assert cm.get_password('testuser1') == 'password1'

    long_password = ''.join(['1111111111' for i in xrange(30)])
    cm.set_password('testuser2', long_password)
    assert cm.get_password('testuser2') == long_password

    cm.delete_password('testuser1')
    with pytest.raises(Exception):
        cm.get_password('testuser1')

    cm.delete_password('testuser2')
    with pytest.raises(Exception):
        cm.get_password('testuser2')


def test_get_session_key(monkeypatch):
    def _mock_session_key_post(self, url, headers=None, **kwargs):
        return common.make_response_record(
            '{"sessionKey":"' + common.SESSION_KEY + '"}')

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.HttpLib, 'post', _mock_session_key_post)

    assert credentials.get_session_key(
        'user', 'password') == common.SESSION_KEY

    with pytest.raises(ValueError):
        credentials.get_session_key('user', 'password', 'non-http')
    credentials.get_session_key('user', 'password', 'http')
    credentials.get_session_key('user', 'password', 'https')
    with pytest.raises(ValueError):
        credentials.get_session_key('user', 'password', 'http', '==')
    credentials.get_session_key('user', 'password', 'http', 'localhost')
    with pytest.raises(ValueError):
        credentials.get_session_key('user', 'password', 'http', 'localhost',
                                    -10)
    credentials.get_session_key('user', 'password', 'http', 'localhost', 10)
