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

'''
This module contains a http request wrapper.
'''

import ssl
import urllib
import urllib2

from solnlib.compression import GzipHandler, ZipHandler

__all__ = ['HTTPRequest']


class HTTPRequest(object):
    '''A wrapper of http request.

    This class provides an easy interface to set http authentication
    and http proxy for http request.

    :param api_user: (optional) API user for http authentication, default
        is None.
    :type api_user: ``string``
    :param api_password: (optional) API password for http authentication,
        default is None.
    :type api_password: ``string``
    :param proxy_server: (optional) Proxy server ip, default is None.
    :type proxy_server: ``string``
    :param proxy_port: (optional) Proxy server port, default is None.
    :type proxy_port: ``integer``
    :param proxy_user: (optional) User for http proxy authentication,
        default is None.
    :type proxy_user: ``string``
    :param proxy_password: (optional) Password for http proxy authentication,
        default is None.
    :param timeout: (optional) Http request timeout, default is 30.
    :type timeout: ``integer``

    Usage::

       >>> from solnlib import http_request
       >>> hq = http_request.HTTPRequest(api_user='admin', api_password='admin',
                                         proxy_server='192.168.1.120', proxy_port=8000,
                                         proxy_user='admin', proxy_password='amdin',
                                         timeout=20)
       >>> content = hq.open('http://host:port/namespace/endpoint',
                             body={'key1': kv1},
                             headers={'h1': hv1})
    '''

    def __init__(self, api_user=None, api_password=None,
                 proxy_server=None, proxy_port=None,
                 proxy_user=None, proxy_password=None, timeout=30):
        self._api_user = api_user
        self._api_password = api_password
        # Proxy handler
        self._proxy_handler = self._get_proxy_handler(
            proxy_server, proxy_port, proxy_user, proxy_password)
        # Https handler
        self._https_handler = urllib2.HTTPSHandler(
            context=ssl._create_unverified_context())

        self._timeout = timeout

    def _get_proxy_handler(self, proxy_server, proxy_port, proxy_user, proxy_password):
        proxy_setting = None
        if proxy_server and proxy_port and proxy_user and proxy_password:
            proxy_setting = 'http://{user}:{password}@{server}:{port}'.format(
                user=proxy_user, password=proxy_password,
                server=proxy_server, port=proxy_port)
        elif proxy_server and proxy_port and proxy_user is None and proxy_password is None:
            proxy_server = 'http://{server}:{port}'.format(
                server=proxy_server, port=proxy_port)
        elif proxy_server or proxy_port or proxy_user or proxy_password:
            raise ValueError('Invalid proxy settings.')

        if proxy_setting:
            return urllib2.ProxyHandler({'http': proxy_server,
                                         'https': proxy_server})
        return None

    def _build_opener(self, url):
        http_handlers = []

        # HTTPS connection handling
        http_handlers.append(self._https_handler)

        # Proxy handling
        if self._proxy_handler:
            http_handlers.append(self._proxy_handler)

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

    def send(self, url, body=None, headers=None):
        '''Send a http request, if body is None will select GET
        method else select POST method.

        :param url: Http request url.
        :type url: ``string``
        :param body: (optional) Http post body, default is None.
        :type body: ``(dict, string)``
        :param headers: (optional) Http request headers, default
            is None.
        :type headers: ``dict``
        :returns: Http request response body.
        :rtype: ``bytes``
        '''

        if isinstance(body, dict):
            body = urllib.urlencode(body)

        args = {}
        if body:
            args['data'] = body
        if headers:
            headers['headers'] = headers
        opener = self._build_opener(url)
        request = urllib2.Request(url, **args)
        response = opener.open(request, timeout=self._timeout)
        content = response.read()
        return self._format_output(content)
