import os.path as op
import socket
import subprocess

from splunklib import binding
from splunklib import client
from splunklib.data import record

cur_dir = op.dirname(op.abspath(__file__))

# Namespace
app = 'unittest'
owner = 'nobody'

# Session key sample
SESSION_KEY = 'nU1aB6BntzwREOnGowa7pN6avV3B6JefliAZIzCX9'


def mock_splunkhome(monkeypatch):
    class _MockPopen(object):
        def __init__(self, args, bufsize=0, executable=None,
                     stdin=None, stdout=None, stderr=None,
                     preexec_fn=None, close_fds=False, shell=False,
                     cwd=None, env=None, universal_newlines=False,
                     startupinfo=None, creationflags=0):
            self._conf = args[1]

        def communicate(self, input=None):
            if self._conf == 'server':
                file_path = op.sep.join(
                    [cur_dir, 'data/mock_splunk/etc/system/default/server.conf'])
            else:
                file_path = op.sep.join(
                    [cur_dir, 'data/mock_splunk/etc/system/default/web.conf'])

            with open(file_path) as fp:
                return fp.read(), None

    monkeypatch.setenv('SPLUNK_HOME', op.join(cur_dir, 'data/mock_splunk/'))
    monkeypatch.setattr(subprocess, 'Popen', _MockPopen)


def mock_serverinfo(monkeypatch):
    _mock_server_info_property = {'server_roles': ['cluster_search_head', 'search_head',
                                                   'kv_store', 'shc_captain'],
                                  'version': '6.3.1511.2',
                                  'serverName': 'unittestServer'}

    monkeypatch.setattr(client.Service, 'info', _mock_server_info_property)


def mock_gethostname(monkeypatch):
    def _mock_gethostname():
        return 'unittestServer'

    monkeypatch.setattr(socket, 'gethostname', _mock_gethostname)


def make_response_record(body, status=200):
    class _MocBufReader(object):
        def __init__(self, buf):
            self._buf = buf

        def read(self, size=None):
            return self._buf

    return record(
        {'body': binding.ResponseReader(_MocBufReader(body)),
         'status': status,
         'reason': '',
         'headers': None})
