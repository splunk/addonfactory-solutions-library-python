import sys
import json
import socket
import StringIO
import os.path as op
import urllib2
import pytest

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import http_request
from splunksolutionlib import credentials


class TestHTTPRequest(object):
    def _mock_credential_get_password1(self, user):
        if user == 'api_user':
            return 'api_user_password'
        else:
            return 'proxy_user_password'

    def _mock_credential_get_password2(self, user):
        raise credentials.CredNotExistException()

    def _mock_urlopen(self, fullurl, data=None,
                      timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        return StringIO.StringIO('{"sessionKey":"OXOm0vqZOfaZPUwGKRmdaAij6fn6X^d"}')

    def test_send(self, monkeypatch):
        monkeypatch.setattr(credentials.CredentialManager, 'get_password',
                            self._mock_credential_get_password1)
        monkeypatch.setattr(urllib2.OpenerDirector, 'open',
                            self._mock_urlopen)


        hq = http_request.HTTPRequest(
            common.SESSION_KEY, 'unittest', realm='realm_test',
            api_user='api_user', proxy_server='192.168.1.120', proxy_port=8000,
            proxy_user='proxy_user', timeout=20)

        content = hq.send('https://localhost:8089/services/auth/login?output_mode=json',
                          body={'username': 'admin', 'password': 'admin'})
        assert json.loads(content)['sessionKey'] == 'OXOm0vqZOfaZPUwGKRmdaAij6fn6X^d'

    def test_send_with_exception(self, monkeypatch):
        monkeypatch.setattr(credentials.CredentialManager, 'get_password',
                            self._mock_credential_get_password2)

        with pytest.raises(credentials.CredNotExistException):
            hq = http_request.HTTPRequest(
                common.SESSION_KEY, 'unittest', realm='realm_test',
                api_user='api_user', proxy_server='192.168.1.120', proxy_port=8000,
                proxy_user='proxy_user', timeout=20)
