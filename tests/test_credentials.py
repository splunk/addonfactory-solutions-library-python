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


class TestCredentialManager(object):
    _credentials_store = {}

    def _mock_storage_passwords_list(self, count=None, **kwargs):
        return TestCredentialManager._credentials_store.values()

    def _mock_storage_passwords_create(self, password, username, realm=None):
        title = '{}:{}:'.format(realm, username) if realm else ':{}:'.format(username)
        password = client.StoragePassword(
            None,
            'storage/passwords/{}'.format(title),
            state=record({'content': {'clear_password': password,
                                      'encr_password': hashlib.md5(password).digest(),
                                      'password': '********',
                                      'realm': realm,
                                      'username': username},
                          'title': title}))
        TestCredentialManager._credentials_store[title] = password
        return password

    def _mock_storage_passwords_delete(self, username, realm=None):
        title = '{}:{}:'.format(realm, username) if realm else ':{}:'.format(username)
        if title in TestCredentialManager._credentials_store:
            del TestCredentialManager._credentials_store[title]
        else:
            raise KeyError('No such entity %s' % username)

    def test_set_password(self, monkeypatch):
        monkeypatch.setattr(client.StoragePasswords, 'list', self._mock_storage_passwords_list)
        monkeypatch.setattr(client.StoragePasswords, 'create', self._mock_storage_passwords_create)
        monkeypatch.setattr(client.StoragePasswords, 'delete', self._mock_storage_passwords_delete)

        cm = credentials.CredentialManager(common.SESSION_KEY, common.app, realm='realm_test')
        cm.set_password('testuser1', 'password1')
        assert cm.get_password('testuser1') == 'password1'

        long_password = ''.join(['1111111111' for i in xrange(30)])
        cm.set_password('testuser2', long_password)
        assert cm.get_password('testuser2') == long_password

    def test_delete_password(self, monkeypatch):
        monkeypatch.setattr(client.StoragePasswords, 'list', self._mock_storage_passwords_list)
        monkeypatch.setattr(client.StoragePasswords, 'delete', self._mock_storage_passwords_delete)
        monkeypatch.setattr(client.StoragePasswords, 'delete', self._mock_storage_passwords_delete)

        cm = credentials.CredentialManager(common.SESSION_KEY, common.app, realm='realm_test')
        cm.delete_password('testuser1')
        with pytest.raises(Exception):
            cm.get_password('testuser1')

        cm.delete_password('testuser2')
        with pytest.raises(Exception):
            cm.get_password('testuser2')


def test_get_session_key(monkeypatch):
    def _mock_session_key_post(self, url, headers=None, **kwargs):
        return common.make_response_record('{"sessionKey":"' + common.SESSION_KEY + '"}')

    monkeypatch.setattr(binding.HttpLib, 'post', _mock_session_key_post)

    assert credentials.get_session_key('user', 'password') == common.SESSION_KEY
