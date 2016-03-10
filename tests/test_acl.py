import sys
import os.path as op
import unittest as ut

import rest_client

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import acl


class TestACL(ut.TestCase):

    def test_acl_manager(self):
        rest_client.setup_acl_env()

        aclm = acl.ACLManager('https', '127.0.0.1', 8089, rest_client.SESSION_KEY)
        perms = aclm.get('data/transforms/extractions/_acl', 'Splunk_TA_test')
        self.assertEqual(perms,
                         {
                             'app': 'Splunk_TA_test',
                             'can_change_perms': True,
                             'can_list': True,
                             'can_share_app': True,
                             'can_share_global': True,
                             'can_share_user': False,
                             'can_write': True,
                             'modifiable': True,
                             'owner': 'nobody',
                             'perms': {'read': ['*'], 'write': ['*']},
                             'removable': False,
                             'sharing': 'global'
                         })

        with self.assertRaises(acl.ACLException):
            aclm.update('data/transforms/extractions', 'Splunk_TA_test', perms_write=['admin'])

        perms = aclm.update('data/transforms/extractions/_acl', 'Splunk_TA_test', perms_write=['admin'])
        self.assertEqual(perms,
                         {
                             'app': 'Splunk_TA_test',
                             'can_change_perms': True,
                             'can_list': True,
                             'can_share_app': True,
                             'can_share_global': True,
                             'can_share_user': False,
                             'can_write': True,
                             'modifiable': True,
                             'owner': 'nobody',
                             'perms': {'read': ['*'], 'write': ['admin']},
                             'removable': False,
                             'sharing': 'global'
                         })

        rest_client.restore_acl_env()


if __name__ == '__main__':
    ut.main(verbosity=2)
