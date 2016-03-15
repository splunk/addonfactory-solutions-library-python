import sys
import hashlib
import os.path as op
import pytest

from splunklib import binding
from splunklib import client
from splunklib.data import record

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import credentials


def test_credential_manager(monkeypatch):
    test_credential_manager._credentials_store = {}

    def _mock_credential_create(self, password, username, realm=None):
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
        test_credential_manager._credentials_store[title] = password

        return password

    def _mock_credential_delete(self, username, realm=None):
        title = '{}:{}:'.format(realm, username) if realm else ':{}:'.format(username)
        if title in test_credential_manager._credentials_store:
            del test_credential_manager._credentials_store[title]
        else:
            raise KeyError("No such entity %s" % username)

    def _mock_credential_list(self, count=None, **kwargs):
        return test_credential_manager._credentials_store.values()

    monkeypatch.setattr(client.StoragePasswords, 'create',
                        _mock_credential_create)
    monkeypatch.setattr(client.StoragePasswords, 'delete',
                        _mock_credential_delete)
    monkeypatch.setattr(client.ReadOnlyCollection, 'list',
                        _mock_credential_list)

    cm = credentials.CredentialManager(common.SESSION_KEY,
                                       'Splunk_TA_test')

    cm.set_password('testuser1', 'password1', realm='realm_test')
    assert cm.get_password(
        'testuser1', realm='realm_test') == 'password1'

    long_password = "".join(['1111111111' for i in xrange(30)])
    cm.set_password('testuser2', long_password, realm='realm_test')
    assert cm.get_password(
        'testuser2', realm='realm_test') == long_password

    cm.delete_password('testuser1', realm='realm_test')
    with pytest.raises(Exception):
        cm.get_password('testuser1', realm='realm_test')

    cm.delete_password('testuser2', realm='realm_test')
    with pytest.raises(Exception):
        cm.get_password('testuser2', realm='realm_test')


def test_get_session_key(monkeypatch):
    def _mock_session_key_post(self, url, headers=None, **kwargs):
        return common.make_response_record(
            '{"sessionKey":"' + common.SESSION_KEY + '"}')

    monkeypatch.setattr(binding.HttpLib, 'post', _mock_session_key_post)

    assert credentials.get_session_key(
        'user', 'password') == common.SESSION_KEY
