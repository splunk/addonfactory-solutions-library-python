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
This module proxy all REST call to splunklib SDK, it handles proxy,
certs etc in this centralized location. All clients should use SplunkRestProxy
to do REST call instead of calling splunklib SDK directly in business logic code
'''

import logging
import traceback

import splunklib.binding as binding
import splunklib.client as client


def _get_proxy_info(context):
    if not context.get("proxy_hostname") or not context.get("proxy_port"):
        return None

    user_pass = ""
    if context.get('proxy_username') and context.get('proxy_password'):
        user_pass = '{user}:{password}@'.format(
            user=context['proxy_username'], password=context['proxy_password'])

    proxy = "http://{user_pass}{host}:{port}".format(
        user_pass=user_pass, host=context["proxy_hostname"],
        port=context["proxy_port"])
    proxies = {
        'http': proxy,
        'https': proxy,
    }
    return proxies


def _request_handler(context):
    '''
    :param context: http connection context can contain the following key/values
    {
    "proxy_hostname": string,
    "proxy_port": int,
    "proxy_username": string,
    "proxy_password": string,
    "key_file": string,
    "cert_file": string,
    }
    :type content: dict
    '''

    try:
        import requests
    except ImportError:
        # FIXME proxy ?
        return binding.handler(
            key_file=context.get('key_file'),
            cert_file=context.get('cert_file'))

    try:
        requests.packages.urllib3.disable_warnings()
    except AttributeError:
        pass

    proxies = _get_proxy_info(context)
    verify = context.get("verify", False)

    if context.get('key_file') and context.get("cert_file"):
        # cert = ('/path/client.cert', '/path/client.key')
        cert = context['key_file'], context['cert_file']
    elif context.get('cert_file'):
        cert = context['cert_file']
    else:
        cert = None

    def request(url, message, **kwargs):
        '''
        :param url: URL
        :type url: string
        :param message: Can contain following key/values
        {
        "method": "GET" or "DELETE", or "PUT" or "POST"
        "headers": [[key, value], [key, value], ...],
        "body": string
        }
        :type message: dict
        '''

        body = message.get('body')
        headers = {
            'User-Agent': 'curl',
            'Accept': '*/*',
            'Connection': 'Keep-Alive',
        }

        if body:
            headers['Content-Length'] = str(len(body))

        for key, value in message['headers']:
            headers[key] = value

        method = message.get('method', 'GET')

        try:
            resp = requests.request(
                method, url, data=body, headers=headers, stream=True,
                verify=verify, proxies=proxies, cert=cert, **kwargs)
        except Exception as e:
            logging.error(
                'Failed to issue http request=%s to url=%s, error=%s',
                method, url, traceback.format_exc(e))
            raise

        return {
            'status': resp.status_code,
            'reason': resp.reason,
            'headers': dict(resp.headers),
            'body': resp.raw,
        }

    return request


class SplunkRestProxy(client.Service):

    def __init__(self, session_key, app, owner='nobody', scheme='https',
                 host='localhost', port=8089, **context):
        '''
        :param context: Other configuration. If `context` contains
        `proxy_hostname`, `proxy_port`, `proxy_username`, `proxy_password`,
        then proxy will be accounted and setup, all REST APIs to Splunkd will
        be through the proxy. If `context` contains `key_file`, `cert_file`,
        then certification will be accounted and setup, all REST APIs to
        Splunkd will use certification
        '''

        handler = _request_handler(context)
        super(SplunkRestProxy, self).__init__(
            handler=handler,
            scheme=scheme,
            host=host,
            port=port,
            token=session_key,
            app=app,
            owner=owner,
            autologin=True)
