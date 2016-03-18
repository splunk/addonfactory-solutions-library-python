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
This module contains a http request wrapper.
"""

import ssl
import urllib
import urllib2
import logging

from splunksolutionlib.credentials import CredentialManager
from splunksolutionlib.credentials import CredNotExistException
from splunksolutionlib.common.codecs import GzipHandler, ZipHandler

__all__ = ['HTTPRequest']


class HTTPRequest(object):
    """A wrapper of http request.

    This class provides an easy interface to set login credential
    and http proxy (should be noticed that the login and proxy
    credential need to be fetched from splunk password storage,
    user just need to input the user names of login and proxy).

    :param session_key: Splunk access token.
    :type session_key: ``string``
    :param app: App name of namespace.
    :type app: ``string``
    :param owner: (optional) Owner of namespace.
    :type owner: ``string``
    :param scheme: (optional) The access scheme, default is `https`.
    :type scheme: ``string``
    :param host: (optional) The host name, default is `localhost`.
    :type host: ``string``
    :param port: (optional) The port number, default is 8089.
    :type port: ``integer``
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, session_key, app, owner='nobody',
                 scheme='https', host='localhost', port=8089, **options):
        # Splunk credential realm
        realm = options.get('realm', None)

        cred_manager = CredentialManager(session_key, app, owner, realm,
                                         scheme, host, port)

        # Http authentication
        self._api_user = options.get('api_user', None)
        if self._api_user:
            try:
                self._api_password = cred_manager.get_password(self._api_user)
            except CredNotExistException:
                logging.error('API user: %s credential could not be found.' % self._api_user)
                raise
        else:
            self._api_password = None

        # Http proxy
        self._proxy_server = options.get('proxy_server', None)
        self._proxy_port = options.get('proxy_port', None)
        self._proxy_user = options.get('proxy_user', None)
        if self._proxy_user:
            try:
                self._proxy_password = cred_manager.get_password(self._proxy_user)
            except CredNotExistException:
                logging.error('Proxy user: %s credential could not be found.' % self._proxy_user)
                raise
        else:
            self._proxy_password = None

        # Http request timeout
        self._timeout = options.get('timeout', self.DEFAULT_TIMEOUT)

    def _build_opener(self, url):
        http_handlers = []

        # HTTPS connection handling
        http_handlers.append(
            urllib2.HTTPSHandler(context=ssl._create_unverified_context()))

        # Proxy handling
        proxy_server = None
        if self._proxy_server and self._proxy_port and self._proxy_user and self._proxy_password:
            proxy_server = 'http://{user}:{password}@{server}:{port}'.format(
                user=self._proxy_user, password=self._proxy_password,
                server=self._proxy_server, port=self._proxy_port)
        elif self._proxy_server is not None and self._proxy_port is not None:
            proxy_server = 'http://{server}:{port}'.format(
                server=self._proxy_server, port=self._proxy_port)
        elif self._proxy_server or self._proxy_port or self._proxy_user or self._proxy_password:
            logging.error('Invalid proxy settings.')

        if proxy_server:
            proxy_handler = urllib2.ProxyHandler({'http': proxy_server,
                                                  'https': proxy_server})
            http_handlers.append(proxy_handler)

        # HTTP auth handling
        if self._api_user and self._api_password:
            http_pwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            http_pwd_mgr.add_password(None, url, self._api_user, self._api_password)
            http_basicauth_handler = urllib2.HTTPBasicAuthHandler(http_pwd_mgr)
            http_digestauth_handler = urllib2.HTTPDigestAuthHandler(http_pwd_mgr)
            http_handlers.extend([http_basicauth_handler, http_digestauth_handler])

        return urllib2.build_opener(*http_handlers)

    def _format_output(self, output):
        if GzipHandler.check_format(output):
            return GzipHandler.decompress(output)
        elif ZipHandler.check_format(output):
            return ZipHandler.decompress(output)
        else:
            return output

    def open(self, url, data=None, headers={}):
        if data is not None:
            data = urllib.urlencode(data)

        opener = self._build_opener(url)
        request = urllib2.Request(url, data=data, headers=headers)
        response = opener.open(request, timeout=self._timeout)
        content = response.read()
        return self._format_output(content)
