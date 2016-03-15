# Copyright 2016 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
This module contains Splunk credential related interfaces.
"""

import re
import json

import splunklib.binding as binding
import splunklib.client as client

__all__ = ['CredException',
           'CredNotExistException',
           'CredentialManager',
           'get_session_key']


class CredException(Exception):
    pass


class CredNotExistException(CredException):
    pass


class CredentialManager(object):
    '''Credential manager.

    This class provides interfaces of CRUD operations on password.

    :param session_key: Splunk access token.
    :type session_key: ``string``
    :param app: App name of namespace.
    :type app: ``string``
    :param owner: (optional) Owner of namespace.
    :type owner: ``string``
    :param scheme: (optional) The scheme for accessing the service, default is `https`.
    :type scheme: ``string``
    :param host: (optional) The host name, default is `localhost`.
    :type host: ``string``
    :param port: (optional) The port number, default is 8089.
    :type port: ``integer``

    Usage::

       >>> import splunksolutionlib.credentials as scc
       >>> cm = scc.CredentialManager(session_key, 'Splunk_TA_test')
    '''

    # Splunk can only encrypt string with length <=255
    SPLUNK_CRED_LEN_LIMIT = 255

    # Splunk credential separator
    SEP = '``splunk_cred_sep``'

    def __init__(self, session_key, app, owner='nobody',
                 scheme='https', host='localhost', port=8089):
        service = client.Service(scheme=scheme,
                                 host=host,
                                 port=port,
                                 token=session_key,
                                 app=app,
                                 owner=owner,
                                 autologin=True)
        self._storage_passwords = service.storage_passwords

    def get_password(self, user, realm=None):
        """Get password.

        :param user: User name of password.
        :type user: ``string``
        :param realm: Realm of password.
        :type realm: ``string``
        :returns: Passwords: {realm:user: clear_password}.
        :rtype: ``dict``

        :raises CredNotExistException: If passwords for realm:user
            doesn't exist.

        Usage::
           >>> import splunksolutionlib.common.credentials as scc
           >>> cm = scc.CredentialManager(session_key, 'Splunk_TA_test')
           >>> cm.get_password('username', 'realm_test')
        """

        all_passwords = self._get_all_passwords()
        for password in all_passwords:
            if password['username'] == user and password['realm'] == realm:
                return password['clear_password']

        raise CredNotExistException(
            'Failed to get password of realm=%s, user=%s.' % (realm, user))

    def set_password(self, user, password, realm=None):
        """Set password.

        :param user: User name of password.
        :type user: ``string``
        :param password: Password of user.
        :type password: ``string``
        :param realm: Realm of password.
        :type realm: ``string``

        Usage::
           >>> import splunksolutionlib.common.credentials as scc
           >>> cm = scc.CredentialManager(session_key, 'Splunk_TA_test')
           >>> cm.set_password('username', 'test_password', 'realm_test')
        """

        try:
            self.delete_password(user, realm)
        except CredException:
            pass

        if len(password) <= self.SPLUNK_CRED_LEN_LIMIT:
            self._storage_passwords.create(password, user, realm)
        else:
            # split the str_to_encrypt when len > 255
            length = 0
            while length < len(password):
                curr_str = password[length:length + self.SPLUNK_CRED_LEN_LIMIT]
                length += self.SPLUNK_CRED_LEN_LIMIT

                partial_user = self.SEP.join(
                    [user, str(length/self.SPLUNK_CRED_LEN_LIMIT)])
                self._storage_passwords.create(curr_str, partial_user, realm)

    def delete_password(self, user, realm=None):
        """Delete password.

        :param user: User name of password.
        :type user: ``string``
        :param realm: Realm of password.
        :type realm: ``string``

        :raises CredNotExistException: If passwords for realm:user
            doesn't exist.

        Usage::
           >>> import splunksolutionlib.common.credentials as scc
           >>> cm = scc.CredentialManager(session_key, 'Splunk_TA_test')
           >>> cm.delete_password('username', 'realm_test')
        """

        deleted = False
        try:
            self._storage_passwords.delete(user, realm)
            deleted = True
        except KeyError:
            ent_pattern = re.compile('.*:(%s%s\d+):' % (user, self.SEP))
            all_passwords = self._storage_passwords.list()

            for password in all_passwords:
                match = ent_pattern.match(password.name)
                if match and password.realm == realm:
                    self._storage_passwords.delete(match.group(1), realm)
                    deleted = True

        if not deleted:
            raise CredNotExistException(
                'Failed to delete password of realm=%s, user=%s' % (
                    realm, user))

    def _get_all_passwords(self):
        all_passwords = self._storage_passwords.list()

        results = {}
        for password in all_passwords:
            match = re.match(r'(.+){}(\d+)'.format(self.SEP), password.name)
            if match:
                actual_name = match.group(1) + ':'
                index = int(match.group(2))
                if actual_name in results:
                    exist_stanza = results[actual_name]
                else:
                    exist_stanza = {}
                    exist_stanza['name'] = actual_name
                    exist_stanza['realm'] = password.realm
                    exist_stanza['username'] = password.username.split(self.SEP)[0]
                    exist_stanza['clears'] = {}
                    results[actual_name] = exist_stanza

                exist_stanza['clears'][index] = password.clear_password
            else:
                results[password.name] = {
                    'name': password.name,
                    'realm': password.realm,
                    'username': password.username,
                    'clear_password': password.clear_password}

        # Merge password by index
        for name, values in results.items():
            field_clear = values.get('clears')
            if field_clear:
                clear_password = ''
                for index in sorted(field_clear.keys()):
                    clear_password += field_clear[index]
                    values['clear_password'] = clear_password

                del values['clears']

        return results.values()


def get_session_key(username, password,
                    scheme='https', host='localhost', port=8089):
    '''Get splunkd access token.

    :param username: The Splunk account username, which is used to
        authenticate the Splunk instance.
    :type username: ``string``
    :param password: The password for the Splunk account.
    :type password: ``string``
    :param scheme: (optional) The scheme for accessing the service, default is `https`.
    :type scheme: ``string``
    :param host: (optional) The host name, default is `localhost`.
    :type host: ``string``
    :param port: (optional) The port number, default is `8089`.
    :type port: ``integer``
    :returns: Splunk access token.
    :rtype: ``string``
    '''

    response = binding.Context().http.post(
        '{}://{}:{}{}'.format(scheme, host, port, '/services/auth/login'),
        username=username,
        password=password,
        output_mode='json')

    return json.loads(response.body.read())['sessionKey']
