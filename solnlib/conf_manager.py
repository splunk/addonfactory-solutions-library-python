# Copyright 2016 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

'''
This module contains simple interfaces for Splunk config file management,
you can update/get/delete stanzas and encrypt/decrypt some fields of stanza
automatically.
'''

import json
import logging
import traceback

from splunklib import binding

from solnlib.utils import retry
from solnlib.credentials import CredentialNotExistException
from solnlib.credentials import CredentialManager
import solnlib.splunk_rest_client as rest_client

__all__ = ['ConfManagerException',
           'ConfStanzaNotExistException',
           'ConfManager']


class ConfManagerException(Exception):
    pass


class ConfStanzaNotExistException(Exception):
    pass


class ConfManager(object):
    '''Configuration file manager.

    :param conf_file: Configuration file.
    :type conf_file: ``string``
    :param session_key: Splunk access token.
    :type session_key: ``string``
    :param app: App name of namespace.
    :type app: ``string``
    :param owner: (optional) Owner of namespace, default is `nobody`.
    :type owner: ``string``
    :param realm: (optional) Realm of credential, default is None.
    :type realm: ``string``
    :param scheme: (optional) The access scheme, default is None.
    :type scheme: ``string``
    :param host: (optional) The host name, default is None.
    :type host: ``string``
    :param port: (optional) The port number, default is None.
    :type port: ``integer``
    :param context: Other configurations for Splunk rest client.
    :type context: ``dict``

    :raises ConfManagerException: If `conf_file` does not exist.

    Usage::

       >>> from solnlib import conf_manager
       >>> cfm = conf_manager.ConfManager('test_conf',
                                          session_key,
                                          'Splunk_TA_test')
    '''

    ENCRYPTED_TOKEN = '******'

    reserved_keys = ('userName', 'appName')

    def __init__(self, conf_file, session_key, app, owner='nobody',
                 scheme=None, host=None, port=None, **context):
        try:
            self._conf_mgr = rest_client.SplunkRestClient(
                session_key,
                app,
                owner=owner,
                scheme=scheme,
                host=host,
                port=port,
                **context).confs[conf_file]
        except KeyError:
            raise ConfManagerException(
                'Config file: %s does not exist.' % conf_file)
        self._conf_file = conf_file
        self._cred_mgr = CredentialManager(
            session_key, app, owner=owner, realm=app,
            scheme=scheme, host=host, port=port, **context)

    def _filter_stanza(self, stanza):
        for k in self.reserved_keys:
            if k in stanza:
                del stanza[k]

        return stanza

    def _encrypt_stanza(self, stanza_name, stanza, encrypt_keys):
        if not encrypt_keys:
            return stanza

        encrypt_fields = {key: stanza[key] for key in encrypt_keys}
        self._cred_mgr.set_password(stanza_name, json.dumps(encrypt_fields))

        for key in encrypt_keys:
            stanza[key] = self.ENCRYPTED_TOKEN

        return stanza

    def _decrypt_stanza(self, stanza_name, encrypted_stanza):
        encrypted_keys = [key for key in encrypted_stanza if
                          encrypted_stanza[key] == self.ENCRYPTED_TOKEN]
        if encrypted_keys:
            encrypted_fields = json.loads(
                self._cred_mgr.get_password(stanza_name))
            for key in encrypted_keys:
                encrypted_stanza[key] = encrypted_fields[key]

        return encrypted_stanza

    def _delete_stanza_creds(self, stanza_name):
        self._cred_mgr.delete_password(stanza_name)

    @retry(exceptions=[binding.HTTPError])
    def get(self, stanza_name):
        '''Get stanza from configuration file.

        :param stanza_name: Stanza name.
        :type stanza_name: ``string``
        :returns: Stanza, like: {
            'disabled': '0',
            'eai:appName': 'solnlib_demo',
            'eai:userName': 'nobody',
            'k1': '1',
            'k2': '2'}
        :rtype: ``dict``

        :raises ConfStanzaNotExistException: If stanza does not exist.

        Usage::

           >>> from solnlib import conf_manager
           >>> cfm = conf_manager.ConfManager('test_conf',
                                              session_key,
                                              'Splunk_TA_test')
           >>> cfm.get('test_stanza')
        '''

        try:
            stanza_mgr = self._conf_mgr.list(name=stanza_name)[0]
        except binding.HTTPError as e:
            if e.status != 404:
                raise

            raise ConfStanzaNotExistException(
                'Stanza: %s does not exist in %s.conf' %
                (stanza_name, self._conf_file))

        stanza = self._decrypt_stanza(stanza_mgr.name, stanza_mgr.content)
        return stanza

    @retry(exceptions=[binding.HTTPError])
    def get_all(self):
        '''Get all stanzas from configuration file.

        :returns: All stanzas, like: {'test': {
            'disabled': '0',
            'eai:appName': 'solnlib_demo',
            'eai:userName': 'nobody',
            'k1': '1',
            'k2': '2'}}
        :rtype: ``dict``

        Usage::

           >>> from solnlib import conf_manager
           >>> cfm = conf_manager.ConfManager('test_conf',
                                              session_key,
                                              'Splunk_TA_test')
           >>> cfm.get_all()
        '''

        stanza_mgrs = self._conf_mgr.list()
        return {stanza_mgr.name: self._decrypt_stanza(
            stanza_mgr.name, stanza_mgr.content) for stanza_mgr in stanza_mgrs}

    @retry(exceptions=[binding.HTTPError])
    def update(self, stanza_name, stanza, encrypt_keys=None):
        '''Update stanza.

        It will try to encrypt the credential automatically fist if
        encrypt_keys are not None else keep stanza untouched.

        :param stanza_name: Stanza name.
        :type stanza_name: ``string``
        :param stanza: Stanza to update, like: {
            'k1': 1,
            'k2': 2}.
        :type stanza: ``dict``
        :param encrypt_keys: Fields name to encrypt.
        :type encrypt_keys: ``list``

        Usage::

           >>> from solnlib import conf_manager
           >>> cfm = conf_manager.ConfManager('test_conf',
                                              session_key,
                                              'Splunk_TA_test')
           >>> cfm.update('test_stanza', {'k1': 1, 'k2': 2}, ['k1'])
        '''

        stanza = self._filter_stanza(stanza)
        encrypted_stanza = self._encrypt_stanza(stanza_name,
                                                stanza,
                                                encrypt_keys)

        try:
            stanza_mgr = self._conf_mgr.list(name=stanza_name)[0]
        except binding.HTTPError as e:
            if e.status != 404:
                raise

            stanza_mgr = self._conf_mgr.create(stanza_name)

        stanza_mgr.submit(encrypted_stanza)

    @retry(exceptions=[binding.HTTPError])
    def delete(self, stanza_name):
        '''Delete stanza.

        :param stanza_name: Stanza name to delete.
        :type stanza_name: ``string``

        :raises ConfStanzaNotExistException: If stanza does not exist.

        Usage::

           >>> from solnlib import conf_manager
           >>> cfm = conf_manager.ConfManager('test_conf',
                                              session_key,
                                              'Splunk_TA_test')
           >>> cfm.delete('test_stanza')
        '''

        try:
            self._cred_mgr.delete_password(stanza_name)
        except CredentialNotExistException:
            pass

        try:
            self._conf_mgr.delete(stanza_name)
        except KeyError as e:
            logging.error('Delete stanza: %s error: %s.',
                          stanza_name, traceback.format_exc(e))
            raise ConfStanzaNotExistException(
                'Stanza: %s does not exist in %s.conf' %
                (stanza_name, self._conf_file))

    @retry(exceptions=[binding.HTTPError])
    def reload(self):
        '''Reload configuration file.

        Usage::

           >>> from solnlib import conf_manager
           >>> cfm = conf_manager.ConfManager('test_conf',
                                              session_key,
                                              'Splunk_TA_test')
           >>> cfm.reload()
        '''

        self._conf_mgr.get('_reload')
