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
This _internal module proxy all REST call to splunklib SDK, it handles proxy
certs etc in this centralized location
'''

import splunklib.client as client


class SplunkRestProxy(client.Service):

    def __init__(self, session_key, app, owner='nobody', scheme='https',
                 host='localhost', port=8089, **context):
        '''
        :param context: Other configuration. If `context` contains
        `proxy_hostname`, `proxy_port`, `proxy_username`, `proxy_password`,
        then proxy will be accounted and setup, all REST APIs to Splunkd will
        be through the proxy. If `context` contains `cert_key`, `cert_file`,
        then certification will be accounted and setup, all REST APIs to
        Splunkd will use certification
        '''

        handler = self._create_http_handler(context)
        super(SplunkRestProxy, self).__init__(
            handler=handler,
            scheme=scheme,
            host=host,
            port=port,
            token=session_key,
            app=app,
            owner=owner,
            autologin=True)

    def _create_http_handler(self, context):
        # FIXME
        return None
