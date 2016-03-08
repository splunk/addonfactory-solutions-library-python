import sys
import os.path as op
import unittest as ut
import hashlib

from splunklib.data import record
import splunklib.binding as binding
import splunklib.client as client

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import splunksolutionlib.credentials as credentials


credentials_store = {}


def _mock_create(self, password, username, realm=None):
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


def _mock_delete(self, username, realm=None):
    global credentials_store

    title = '{}:{}:'.format(realm, username) if realm else ':{}:'.format(username)
    if title in credentials_store:
        del credentials_store[title]
    else:
        raise KeyError("No such entity %s" % username)


def _mock_list(self, count=None, **kwargs):
    global credentials_store

    return credentials_store.values()


class TestCredentials(ut.TestCase):

    def test_get_session_key(self):
        def _mock_post(self, url, headers=None, **kwargs):
            class _MocBufReader(object):
                def __init__(self, buf):
                    self._buf = buf

                def read(self, size=None):
                    return self._buf

            return record(
                {'body': binding.ResponseReader(_MocBufReader('<response>\n  <sessionKey>W5l05ATp_CuWFwDg29z6zz2TZMtYb5d6wrVK^qBOVXZfvgadV1GscFcb8QWq3l7V_drv94R1kHMX1Ttx_ow^Ig_0EZH4AFFfX_QhuIN</sessionKey>\n</response>')),
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

        old_post = binding.HttpLib.post
        binding.HttpLib.post = _mock_post

        self.assertEqual(credentials.get_session_key('https', 'localhost', 8089, 'user', 'password'),
                         'W5l05ATp_CuWFwDg29z6zz2TZMtYb5d6wrVK^qBOVXZfvgadV1GscFcb8QWq3l7V_drv94R1kHMX1Ttx_ow^Ig_0EZH4AFFfX_QhuIN')

        binding.HttpLib.post = old_post

    def test_credential_manager(self):

        old_list = client.ReadOnlyCollection.list
        client.ReadOnlyCollection.list = _mock_list
        old_create = client.StoragePasswords.create
        client.StoragePasswords.create = _mock_create
        old_delete = client.StoragePasswords.delete
        client.StoragePasswords.delete = _mock_delete

        cm = credentials.CredentialManager('https', '127.0.0.1', 8089,
                                           'W5l05ATp_CuWFwDg29z6zz2TZMtYb5d6wrVK^qBOVXZfvgadV1GscFcb8QWq3l7V_drv94R1kHMX1Ttx_ow^Ig_0EZH4AFFfX_QhuIN')

        cm.set_password('testuser1', 'password1', 'app-test', realm='realm_test')
        self.assertEqual(cm.get_password('testuser1', 'app-test', realm='realm_test'),
                         'password1')

        long_password = "".join(['1111111111' for i in xrange(30)])
        cm.set_password('testuser2', long_password, 'app-test', realm='realm_test')
        self.assertEqual(cm.get_password('testuser2', 'app-test', realm='realm_test'),
                         long_password)

        cm.delete_password('testuser1', 'app-test', realm='realm_test')
        with self.assertRaises(Exception):
            cm.get_password('testuser1', 'app-test', realm='realm_test')

        cm.delete_password('testuser2', 'app-test', realm='realm_test')
        with self.assertRaises(Exception):
            cm.get_password('testuser2', 'app-test', realm='realm_test')

        client.ReadOnlyCollection.list = old_list
        client.StoragePasswords.create = old_create
        client.StoragePasswords.delete = old_delete


if __name__ == '__main__':
    ut.main(verbosity=2)
