import sys
import os.path as op
import unittest as ut

import rest_client

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import splunksolutionlib.credentials as credentials


class TestCredentials(ut.TestCase):

    def test_get_session_key(self):
        rest_client.setup_session_key_env()

        self.assertEqual(credentials.get_session_key('https', 'localhost', 8089, 'user', 'password'),
                         rest_client.SESSION_KEY)

        rest_client.restore_session_key_env()

    def test_credential_manager(self):
        rest_client.setup_credential_env()

        cm = credentials.CredentialManager('https', '127.0.0.1', 8089, rest_client.SESSION_KEY)

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

        rest_client.restore_credential_env()


if __name__ == '__main__':
    ut.main(verbosity=2)
