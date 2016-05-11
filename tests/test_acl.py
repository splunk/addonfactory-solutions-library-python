import sys
import os.path as op
import json
import pytest

from splunklib import binding

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import acl

_old_acl = '{"entry": [{"author": "nobody", "name": "transforms", "acl": {"sharing": "global", "perms": {"read": ["*"], "write": ["*"]}, "app": "unittest", "modifiable": true, "owner": "nobody", "can_change_perms": true, "can_share_global": true, "can_list": true, "can_share_user": false, "can_share_app": true, "removable": false, "can_write": true}}]}'

_new_acl1 = '{"entry": [{"author": "nobody", "name": "transforms", "acl": {"sharing": "global", "perms": {"read": ["admin"], "write": ["admin"]}, "app": "unittest", "modifiable": true, "owner": "nobody", "can_change_perms": true, "can_share_global": true, "can_list": true, "can_share_user": false, "can_share_app": true, "removable": false, "can_write": true}}]}'

_new_acl2 = '{"entry": [{"author": "nobody", "name": "transforms", "acl": {"sharing": "global", "perms": {"read": ["admin"], "write": ["*"]}, "app": "unittest", "modifiable": true, "owner": "nobody", "can_change_perms": true, "can_share_global": true, "can_list": true, "can_share_user": false, "can_share_app": true, "removable": false, "can_write": true}}]}'

_new_acl3 = '{"entry": [{"author": "nobody", "name": "transforms", "acl": {"sharing": "global", "perms": {"read": ["*"], "write": ["admin"]}, "app": "unittest", "modifiable": true, "owner": "nobody", "can_change_perms": true, "can_share_global": true, "can_list": true, "can_share_user": false, "can_share_app": true, "removable": false, "can_write": true}}]}'


def _mock_get(self, path_segment, owner=None, app=None, sharing=None, **query):
    return common.make_response_record(_old_acl)


def _mock_post(self, path_segment, owner=None, app=None, sharing=None, headers=None, **query):
    if 'perms.read=admin' in query['body'] and 'perms.write=admin' in query['body']:
            return common.make_response_record(_new_acl1)
    elif 'perms.read=admin' in query['body']:
        return common.make_response_record(_new_acl2)
    elif 'perms.write=admin' in query['body']:
        return common.make_response_record(_new_acl3)
    else:
        return common.make_response_record(_old_acl)


class TestACLManager(object):
    def test_get(self, monkeypatch):
        monkeypatch.setattr(binding.Context, 'get', _mock_get)

        aclm = acl.ACLManager(common.SESSION_KEY, common.app)
        perms = aclm.get('data/transforms/extractions/_acl')
        assert perms == json.loads(_old_acl)['entry'][0]['acl']

    def test_update(self, monkeypatch):
        monkeypatch.setattr(binding.Context, 'get', _mock_get)
        monkeypatch.setattr(binding.Context, 'post', _mock_post)

        aclm = acl.ACLManager(common.SESSION_KEY, common.app)

        perms = aclm.update('data/transforms/extractions/_acl',
                            perms_read=['admin'], perms_write=['admin'])
        assert perms == json.loads(_new_acl1)['entry'][0]['acl']

        perms = aclm.update('data/transforms/extractions/_acl',
                            perms_read=['admin'])
        assert perms == json.loads(_new_acl2)['entry'][0]['acl']

        perms = aclm.update('data/transforms/extractions/_acl',
                            perms_write=['admin'])
        assert perms == json.loads(_new_acl3)['entry'][0]['acl']

        perms = aclm.update('data/transforms/extractions/_acl')
        assert perms == json.loads(_old_acl)['entry'][0]['acl']

        with pytest.raises(acl.ACLException):
            aclm.update('data/transforms/extractions', perms_write=['admin'])
