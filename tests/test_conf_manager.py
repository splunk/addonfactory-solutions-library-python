import hashlib
import os.path as op
import sys

import pytest

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import conf_manager
from splunklib import binding
from splunklib import client
from splunklib.data import record


def test_conf_manager(monkeypatch):
    credentials_store = {}
    all_stanzas = {}

    def mock_storage_passwords_list(self, count=None, **kwargs):
        return credentials_store.values()

    def mock_storage_passwords_create(self, password, username, realm=None):
        title = '{}:{}:'.format(realm, username) if \
                realm else ':{}:'.format(username)
        password = client.StoragePassword(
            None,
            'storage/passwords/{}'.format(title),
            state=record({'content': {'clear_password': password,
                                      'encr_password': hashlib.md5(
                                          password.encode()).digest(),
                                      'password': '********',
                                      'realm': realm,
                                      'username': username},
                          'title': title}))
        credentials_store[title] = password
        return password

    def mock_storage_passwords_delete(self, username, realm=None):
        title = '{}:{}:'.format(realm, username) if \
                realm else ':{}:'.format(username)
        if title in credentials_store:
            del credentials_store[title]
        else:
            raise KeyError('No such entity %s' % username)

    def mock_storage_password_delete(self):
        if self.name in credentials_store:
            del credentials_store[self.name]
        else:
            raise KeyError('No such entity %s' % self.name)

    def mock_configuration_get(
            self, name='', owner=None, app=None, sharing=None, **query):
        return common.make_response_record('')

    def mock_configuration_file_list(self, count=None, **kwargs):
        if not hasattr(mock_configuration_file_list, 'normal_mode'):
            mock_configuration_file_list.normal_mode = True
            raise binding.HTTPError(common.make_response_record('', status=404))
        else:
            if 'name' in kwargs:
                if kwargs['name'] in all_stanzas:
                    stanza_mgr = client.Stanza(
                        self.service,
                        'configs/conf-test/{0}/'.format(kwargs['name']),
                        skip_refresh=True)
                    stanza_mgr._state = common.record(
                        {'title': kwargs['name'],
                         'access': common.record({'app': 'test'}),
                         'content': all_stanzas[kwargs['name']]})
                    return [stanza_mgr]
                else:
                    raise binding.HTTPError(
                        common.make_response_record('', status=404))
            else:
                stanza_mgrs = []
                for stanza_name, stanza in list(all_stanzas.items()):
                    stanza_mgr = client.Stanza(
                        self.service,
                        'configs/conf-test/{0}/'.format(stanza_name),
                        skip_refresh=True)
                    stanza_mgr._state = common.record({'title': stanza_name,
                                                       'access': common.record({'app': 'test'}),
                                                       'content': stanza})
                    stanza_mgrs.append(stanza_mgr)

                return stanza_mgrs

    def mock_configuration_file_get(
            self, name="", owner=None, app=None, sharing=None, **query):
        return common.make_response_record('')

    def mock_configuration_file_create(self, name, **params):
        stanza_mgr = client.Stanza(
            self.service,
            'configs/conf-test/{0}/'.format(name),
            skip_refresh=True)
        stanza_mgr._state = common.record({'title': name,
                                           'content': {}})
        return stanza_mgr

    def mock_configuration_file_delete(self, name, **params):
        del all_stanzas[name]

    def mock_stanza_submit(self, stanza):
        all_stanzas[self.name] = stanza

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(client.StoragePasswords, 'list',
                        mock_storage_passwords_list)
    monkeypatch.setattr(client.StoragePasswords, 'create',
                        mock_storage_passwords_create)
    monkeypatch.setattr(client.StoragePasswords, 'delete',
                        mock_storage_passwords_delete)
    monkeypatch.setattr(client.StoragePassword, 'delete',
                        mock_storage_password_delete)
    monkeypatch.setattr(client.Configurations, 'get',
                        mock_configuration_get)
    monkeypatch.setattr(client.ConfigurationFile, 'get',
                        mock_configuration_file_get)
    monkeypatch.setattr(client.ConfigurationFile, 'list',
                        mock_configuration_file_list)
    monkeypatch.setattr(client.ConfigurationFile, 'create',
                        mock_configuration_file_create)
    monkeypatch.setattr(client.ConfigurationFile, 'delete',
                        mock_configuration_file_delete)
    monkeypatch.setattr(client.Stanza, 'submit',
                        mock_stanza_submit)

    cfm = conf_manager.ConfManager(common.SESSION_KEY, common.app)
    conf = cfm.get_conf('test')
    assert not conf.stanza_exist('test_stanza')
    conf.update('test_stanza', {'k1': 1, 'k2': 2}, ['k1', 'key_not_exist'])
    assert conf.get('test_stanza') == {'k2': 2, 'k1': 1, 'eai:access':common.record({'app': 'test'}), 'eai:appName': 'test'}
    assert conf.get_all() == {'test_stanza': {'k2': 2, 'k1': 1, 'eai:access':common.record({'app': 'test'}), 'eai:appName': 'test'}}

    conf.delete('test_stanza')
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.get('test_stanza')
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.delete('test_stanza')
    conf.reload()

    cfm = conf_manager.ConfManager(common.SESSION_KEY,common.app,realm='__REST_CREDENTIAL__#{}#configs/conf-test'.format(common.app))
    conf = cfm.get_conf('test')
    assert not conf.stanza_exist('test_stanza')
    conf.update('test_stanza', {'k1': 1, 'k2': 2}, ['k1','key_not_exist'])
    assert conf.get('test_stanza') == {'k2': 2, 'k1': 1, 'eai:access':common.record({'app': 'test'}), 'eai:appName': 'test'}
    assert conf.get_all() == {'test_stanza': {'k2': 2, 'k1': 1, 'eai:access':common.record({'app': 'test'}), 'eai:appName': 'test'}}

    conf.delete('test_stanza')
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.get('test_stanza')
    with pytest.raises(conf_manager.ConfStanzaNotExistException):
        conf.delete('test_stanza')
    conf.reload()
