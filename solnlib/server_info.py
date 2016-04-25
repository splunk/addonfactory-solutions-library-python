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
This module contains splunk server info related functionalities.
'''

import json

from splunklib import binding

from solnlib.utils import retry
import solnlib.splunk_rest_client as rest_client

__all__ = ['ServerInfo']


class ServerInfo(object):
    '''This class is a wrapper of splunk server info.

    :param session_key: Splunk access token.
    :type session_key: ``string``
    :param scheme: (optional) The access scheme, default is `https`.
    :type scheme: ``string``
    :param host: (optional) The host name, default is `localhost`.
    :type host: ``string``
    :param port: (optional) The port number, default is 8089.
    :type port: ``integer``
    :param context: Other configurations for Splunk rest client.
    :type context: ``dict``
    '''

    SHC_MEMBER_ENDPOINT = '/services/shcluster/member/members'

    def __init__(self, session_key,
                 scheme='https', host='localhost', port=8089, **context):
        self._session_key = session_key
        self._scheme = scheme
        self._host = host
        self._port = port
        self._context = context
        self._rest_client = rest_client.SplunkRestClient(session_key,
                                                         '-',
                                                         scheme=scheme,
                                                         host=host,
                                                         port=port,
                                                         **context)
        self._server_info = self._get_server_info()

    @retry(exceptions=[binding.HTTPError])
    def _get_server_info(self):
        return self._rest_client.info

    @property
    def server_name(self):
        '''Get server name.

        :returns: Server name.
        :rtype: ``string``
        '''

        return self._server_info['serverName']

    @property
    def version(self):
        '''Get splunk server version.

        :returns: Splunk server version.
        :rtype: ``string``
        '''

        return self._server_info['version']

    def is_captain(self):
        '''Check if this server is SHC captain.

        :returns: True if this server is SHC captain else False.
        :rtype: ``bool``
        '''

        return 'shc_captain' in self._server_info['server_roles']

    def is_cloud_instance(self):
        '''Check if this server is a cloud instance.

        :returns: True if this server is a cloud instance else False.
        :rtype: ``bool``
        '''

        try:
            return self._server_info['instance_type'] == 'cloud'
        except KeyError:
            return False

    def is_search_head(self):
        '''Check if this server is a search head.

        :returns: True if this server is a search head else False.
        :rtype: ``bool``
        '''

        server_info = self._server_info
        for sh in ('search_head', 'cluster_search_head'):
            if sh in server_info['server_roles']:
                return True

        return False

    def is_shc_member(self):
        '''Check if this server is a SHC member.

        :returns: True if this server is a SHC member else False.
        :rtype: ``bool``
        '''

        return 'cluster_search_head' in self._server_info['server_roles']

    @retry(exceptions=[binding.HTTPError])
    def get_shc_members(self):
        '''Get SHC members.

        :returns: List of SHC members [(label, peer_scheme_host_port) ...]
        :rtype: ``list``

        :Raises splunklib.binding.HTTPError: If endpoint doesn't exist.
        '''

        content = self._rest_client.get(self.SHC_MEMBER_ENDPOINT,
                                        output_mode='json').body.read()
        members = []
        for member in json.loads(content)['entry']:
            content = member['content']
            members.append((content['label'],
                            content['peer_scheme_host_port']))

        return members
