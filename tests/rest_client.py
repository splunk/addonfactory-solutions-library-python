import hashlib

from splunklib.data import record
from splunklib import binding
from splunklib import client


class _MocBufReader(object):
    def __init__(self, buf):
        self._buf = buf

    def read(self, size=None):
        return self._buf


# Session key
# ================================================================================
_session_key_post_backup = binding.HttpLib.post

SESSION_KEY = 'W5l05ATp_CuWFwDg29z6zz2TZMtYb5d6wrVK^qBOVXZfvgadV1GscFcb8QWq3l7V_drv94R1kHMX1Ttx_ow^Ig_0EZH4AFFfX_QhuIN'


def _mock_session_key_post(self, url, headers=None, **kwargs):
    return record(
        {'body': binding.ResponseReader(_MocBufReader('{"sessionKey":"' + SESSION_KEY + '"}')),
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
    binding.HttpLib.post = _session_key_post_backup


# Credential
# ================================================================================
_credential_list_backup = client.ReadOnlyCollection.list
_credential_create_backup = client.StoragePasswords.create
_credential_delete_backup = client.StoragePasswords.delete


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
    client.ReadOnlyCollection.list = _credential_list_backup
    client.StoragePasswords.create = _credential_create_backup
    client.StoragePasswords.delete = _credential_delete_backup

# ACL
# ================================================================================
_acl_get_backup = binding.Context.get
_acl_post_backup = binding.Context.post

_acl_get_body = '{"entry": [{"author": "nobody", "name": "transforms", "acl": {"sharing": "global", "perms": {"read": ["*"], "write": ["*"]}, "app": "Splunk_TA_test", "modifiable": true, "owner": "nobody", "can_change_perms": true, "can_share_global": true, "can_list": true, "can_share_user": false, "can_share_app": true, "removable": false, "can_write": true}}]}'

_acl_post_body = '{"entry": [{"author": "nobody", "name": "transforms", "acl": {"sharing": "global", "perms": {"read": ["*"], "write": ["admin"]}, "app": "Splunk_TA_test", "modifiable": true, "owner": "nobody", "can_change_perms": true, "can_share_global": true, "can_list": true, "can_share_user": false, "can_share_app": true, "removable": false, "can_write": true}}]}'


def _mock_acl_get(self, path_segment, owner=None, app=None, sharing=None, **query):
    return record(
        {'body': binding.ResponseReader(_MocBufReader(_acl_get_body)),
         'headers': [('content-length', '39903'),
                     ('x-content-type-options', 'nosniff'),
                     ('expires', 'Thu, 26 Oct 1978 00:00:00 GMT'),
                     ('vary', 'Authorization'),
                     ('server', 'Splunkd'),
                     ('connection', 'Close'),
                     ('cache-control', 'no-store, no-cache, must-revalidate, max-age=0'),
                     ('date', 'Fri, 11 Mar 2016 03:15:57 GMT'),
                     ('x-frame-options', 'SAMEORIGIN'),
                     ('content-type', 'application/json; charset=UTF-8')],
         'reason': 'OK',
         'status': 200})


def _mock_acl_post(self, path_segment, owner=None, app=None, sharing=None, headers=None, **query):
    return record(
        {'body': binding.ResponseReader(_MocBufReader(_acl_post_body)),
         'headers': [('content-length', '39903'),
                     ('x-content-type-options', 'nosniff'),
                     ('expires', 'Thu, 26 Oct 1978 00:00:00 GMT'),
                     ('vary', 'Authorization'),
                     ('server', 'Splunkd'),
                     ('connection', 'Close'),
                     ('cache-control', 'no-store, no-cache, must-revalidate, max-age=0'),
                     ('date', 'Fri, 11 Mar 2016 03:15:57 GMT'),
                     ('x-frame-options', 'SAMEORIGIN'),
                     ('content-type', 'application/json; charset=UTF-8')],
         'reason': 'OK',
         'status': 200}
    )


def setup_acl_env():
    binding.Context.get = _mock_acl_get
    binding.Context.post = _mock_acl_post


def restore_acl_env():
    binding.Context.get = _acl_get_backup
    binding.Context.post = _acl_post_backup

# Server info
# ================================================================================
_server_info_get_backup = binding.Context.get

_server_info_get_body = '{"entry": [{"content": {"server_roles": ["cluster_search_head", "search_head", "kv_store", "shc_captain"], "version": "6.3.1511.2"}}]}'

_shc_get_body = '{"entry": [{"name": "5B4A53C7-B824-4103-B8CC-C22E1EC6480F", "content": {"peer_scheme_host_port": "https://192.168.1.85:8089", "label": "SHC01_SearchHead02_1_85"}}, {"name": "D7E3BA03-85CE-449A-9736-38F2DA58236B", "content": {"peer_scheme_host_port": "https://192.168.1.86:8089", "label": "SHC01_SearchHead03_1_86"}}, {"name": "DA72938A-72C4-46F3-86BE-2E200EC56C76", "content": {"peer_scheme_host_port": "https://192.168.1.84:8089", "label": "SHC01_SearchHead01_1_84"}}]}'


def _mock_server_info_get(self, path_segment, owner=None, app=None, sharing=None, **query):
    if path_segment == '/services/server/info/server-info':
        body = _server_info_get_body
    else:
        body = _shc_get_body

    return record(
        {'body': binding.ResponseReader(_MocBufReader(body)),
         'headers': [('content-length', '39903'),
                     ('x-content-type-options', 'nosniff'),
                     ('expires', 'Thu, 26 Oct 1978 00:00:00 GMT'),
                     ('vary', 'Authorization'),
                     ('server', 'Splunkd'),
                     ('connection', 'Close'),
                     ('cache-control', 'no-store, no-cache, must-revalidate, max-age=0'),
                     ('date', 'Fri, 11 Mar 2016 03:15:57 GMT'),
                     ('x-frame-options', 'SAMEORIGIN'),
                     ('content-type', 'application/json; charset=UTF-8')],
         'reason': 'OK',
         'status': 200})


def setup_server_info_env():
    binding.Context.get = _mock_server_info_get


def restore_server_info_env():
    binding.Context.get = _server_info_get_backup
