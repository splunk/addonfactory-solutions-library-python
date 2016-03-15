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
This module contains interfaces that support CRUD operations on ACL.
"""

import json

from splunklib import binding

__all__ = ['ACLException',
           'ACLManager']


class ACLException(Exception):
    pass


class ACLManager(object):
    '''ACL Manager.

    This class provides interfaces of CRUD operations on ACL.

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

       >>> import splunksolutionlib.acl as sacl
       >>> saclm = sacl.ACLManager(session_key, 'Splunk_TA_test')
       >>> saclm.get('data/transforms/extractions')
       >>> saclm.update('data/transforms/extractions/_acl',
                        perms_read=['*'], perms_write=['*'])
    '''

    def __init__(self, session_key, app, owner='nobody',
                 scheme='https', host='localhost', port=8089):
        self._binding_context = binding.Context(scheme=scheme,
                                                host=host,
                                                port=port,
                                                token=session_key,
                                                app=app,
                                                owner=owner,
                                                autologin=True)

    def get(self, path):
        '''Get ACL of  /servicesNS/owner/app/{`path`}.

        :param path: Path of ACL relative to /servicesNS/{`owner`}/{`app`}
        :type path: ``string``
        :returns: A dict contains ACL.
        :rtype: ``dict``
        '''

        content = self._binding_context.get(path,
                                            output_mode='json').body.read()

        return json.loads(content)['entry'][0]['acl']

    def update(self, path, owner=None, perms_read=None, perms_write=None):
        '''Update ACL of /servicesNS/{`owner`}/{`app`}/{`path`}.

        If the ACL is per-entity (ends in /acl), owner can be reassigned. If
        the acl is endpoint-level (ends in _acl), owner will be ignored. The
        "sharing" setting is always retrieved from the current.

        :param path: Path of ACL relative to /servicesNS/{owner}/{app}. MUST
            contain /acl or /_acl indicating whether the permission is applied
            at the per-entity level or endpoint level, respectively.
        :type path: ``string``
        :param owner: (optional) New owner of ACL.
        :type owner: ``string``
        :param perms_read: list of roles (['*'] for all roles).
            If unspecified we will POST with current (if available) perms.read.
        :type perms_read: ``list``
        :param perms_write: list of roles (['*'] for all roles).
            If unspecified we will POST with current (if available) perms.write
        :type perms_write: ``list``
        :returns: A dict contains ACL after update.
        :rtype: ``dict``

        :raises ACLException: If `path` doesn't end by 'acl/_acl'.
        '''

        if not path.endswith('/acl') and not path.endswith('/_acl'):
            raise ACLException(
                'Endpoint: %s must end with /acl or /_acl.' % path)

        curr_acl = self.get(path)

        postargs = {}
        if perms_read and perms_write:
            postargs = {'perms.read': ','.join(perms_read),
                        'perms.write': ','.join(perms_write)}
        elif perms_read:
            curr_write = curr_acl['perms'].get('write', [])

            if curr_write:
                postargs = {'perms.read': ','.join(perms_read),
                            'perms.write': ','.join(curr_write)}
            else:
                postargs = {'perms.read': ','.join(perms_read)}
        elif perms_write:
            curr_read = curr_acl['perms'].get('read', [])

            if curr_read:
                postargs = {'perms.read': ','.join(curr_read),
                            'perms.write': ','.join(perms_write)}
            else:
                postargs = {'perms.write': ','.join(perms_write)}

        if path.endswith('/acl'):
            # Allow ownership to be reset only at entity level.
            postargs['owner'] = owner or curr_acl['owner']

        postargs['sharing'] = curr_acl['sharing']

        content = self._binding_context.post(path,
                                             owner=curr_acl['owner'],
                                             app=curr_acl['app'],
                                             body=binding._encode(**postargs),
                                             output_mode='json').body.read()

        return json.loads(content)['entry'][0]['acl']
