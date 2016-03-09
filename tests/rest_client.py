import hashlib

from splunklib.data import record
import splunklib.binding as binding
import splunklib.client as client


class _MocBufReader(object):
    def __init__(self, buf):
        self._buf = buf

    def read(self, size=None):
        return self._buf


# Session key
# ================================================================================
session_key_post_backup = binding.HttpLib.post

SESSION_KEY = 'W5l05ATp_CuWFwDg29z6zz2TZMtYb5d6wrVK^qBOVXZfvgadV1GscFcb8QWq3l7V_drv94R1kHMX1Ttx_ow^Ig_0EZH4AFFfX_QhuIN'


def _mock_session_key_post(self, url, headers=None, **kwargs):
    return record(
        {'body': binding.ResponseReader(_MocBufReader('<response>\n  <sessionKey>{}</sessionKey>\n</response>'.format(SESSION_KEY))),
         'headers': [
             ('content-length', '154'),
             ('x-content-type-options', 'nosniff'),
             ('expires', 'Thu, 26 Oct 1978 00:00:00 GMT'),
             ('server', 'Splunkd'),
             ('connection', 'Close'),
             ('cache-control', 'no-store, no-cache, must-revalidate, max-age=0'),
             ('date', 'Wed, 09 Mar 2016 02:35:34 GMT'),
             ('x-frame-options', 'SAMEORIGIN'),
             ('content-type', 'text/xml; charset=UTF-8')],
         'reason': 'OK',
         'status': 200})


def setup_session_key_env():
    binding.HttpLib.post = _mock_session_key_post


def restore_session_key_env():
    binding.HttpLib.post = _mock_session_key_post


# Credential
# ================================================================================
credential_list_backup = client.ReadOnlyCollection.list
credential_create_backup = client.StoragePasswords.create
credential_delete_backup = client.StoragePasswords.delete


credentials_store = {}


def _mock_credential_create(self, password, username, realm=None):
    global credentials_store

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
    credentials_store[title] = password

    return password


def _mock_credential_delete(self, username, realm=None):
    global credentials_store

    title = '{}:{}:'.format(realm, username) if realm else ':{}:'.format(username)
    if title in credentials_store:
        del credentials_store[title]
    else:
        raise KeyError("No such entity %s" % username)


def _mock_credential_list(self, count=None, **kwargs):
    global credentials_store

    return credentials_store.values()


def setup_credential_env():
    client.ReadOnlyCollection.list = _mock_credential_list
    client.StoragePasswords.create = _mock_credential_create
    client.StoragePasswords.delete = _mock_credential_delete


def restore_credential_env():
    client.ReadOnlyCollection.list = credential_list_backup
    client.StoragePasswords.create = credential_create_backup
    client.StoragePasswords.delete = credential_delete_backup
