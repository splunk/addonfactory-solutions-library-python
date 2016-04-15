import sys
import json
import socket
import StringIO
import os.path as op
import urllib2

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import http_request


class TestHTTPRequest(object):
    def test_send(self, monkeypatch):
        def _mock_urlopen(self, fullurl, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
            return StringIO.StringIO('{"sessionKey":"' + common.SESSION_KEY + '"}')

        monkeypatch.setattr(urllib2.OpenerDirector, 'open', _mock_urlopen)

        hq = http_request.HTTPRequest(api_user='admin', api_password='admin',
                                      proxy_server='192.168.1.120', proxy_port=8000,
                                      proxy_user='admin', proxy_password='admin', timeout=20)
        content = hq.send('https://localhost:8089/services/auth/login?output_mode=json',
                          body={'username': 'admin', 'password': 'admin'})
        assert json.loads(content)['sessionKey'] == common.SESSION_KEY
