import sys
import os
import os.path as op
import subprocess
import socket

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import splunkenv


class _MockPopen(object):
    def __init__(self, args, bufsize=0, executable=None,
                 stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=False, shell=False,
                 cwd=None, env=None, universal_newlines=False,
                 startupinfo=None, creationflags=0):
        self._conf = args[1]

    def communicate(self, input=None):
        cur_dir = op.dirname(op.abspath(__file__))
        if self._conf == 'server':
            file_path = op.sep.join(
                [cur_dir, 'data', 'unittest/server.conf'])
        else:
            file_path = op.sep.join(
                [cur_dir, 'data', 'unittest/web.conf'])

        with open(file_path) as fp:
            return fp.read(), None


def test_splunkhome_path(monkeypatch):
    monkeypatch.setenv('SPLUNK_HOME', '/opt/splunk/')
    monkeypatch.setattr(subprocess, 'Popen', _MockPopen)

    splunkhome_path = splunkenv.make_splunkhome_path(['etc', 'apps'])
    assert splunkhome_path == os.environ['SPLUNK_HOME'] + 'etc/apps'


def test_get_splunk_host_info(monkeypatch):
    def _mock_gethostname():
        return 'testServer'

    monkeypatch.setenv('SPLUNK_HOME', '/opt/splunk/')
    monkeypatch.setattr(subprocess, 'Popen', _MockPopen)
    monkeypatch.setattr(socket, 'gethostname', _mock_gethostname)

    server_name, host_name = splunkenv.get_splunk_host_info()
    assert server_name == 'testServer'
    assert host_name == 'testServer'


def test_splunk_bin(monkeypatch):
    monkeypatch.setenv('SPLUNK_HOME', '/opt/splunk/')
    monkeypatch.setattr(subprocess, 'Popen', _MockPopen)

    splunk_bin = splunkenv.get_splunk_bin()
    assert splunk_bin in (os.environ['SPLUNK_HOME'] + 'bin/splunk',
                          os.environ['SPLUNK_HOME'] + 'bin/splunk.exe')


def test_get_splunkd_access_info(monkeypatch):
    monkeypatch.setenv('SPLUNK_HOME', '/opt/splunk/')
    monkeypatch.setattr(subprocess, 'Popen', _MockPopen)

    scheme, host, port = splunkenv.get_splunkd_access_info()
    assert scheme == 'https'
    assert host == '127.0.0.1'
    assert port == 8089


def test_splunkd_uri(monkeypatch):
    monkeypatch.setenv('SPLUNK_HOME', '/opt/splunk/')
    monkeypatch.setattr(subprocess, 'Popen', _MockPopen)

    uri = splunkenv.get_splunkd_uri()
    assert uri == 'https://127.0.0.1:8089'

    monkeypatch.setenv('SPLUNK_BINDIP', '10.0.0.2:7080')
    uri = splunkenv.get_splunkd_uri()
    assert uri == 'https://10.0.0.2:8089'

    monkeypatch.setenv('SPLUNK_BINDIP', '10.0.0.3')
    uri = splunkenv.get_splunkd_uri()
    assert uri == 'https://10.0.0.3:8089'

    monkeypatch.setenv('SPLUNKD_URI', 'https://10.0.0.1:8089')
    uri = splunkenv.get_splunkd_uri()
    assert uri == 'https://10.0.0.1:8089'
