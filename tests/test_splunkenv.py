import sys
import os
import os.path as op
import unittest as ut
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
            file_path = op.sep.join([cur_dir, 'data', 'conf', 'server.conf'])
        elif self._conf == 'web':
            file_path = op.sep.join([cur_dir, 'data', 'conf', 'web.conf'])
        else:
            raise ValueError('Unknown conf file %s.' % self._conf)

        with open(file_path) as fp:
            return fp.read(), None


def _mock_gethostname():
    return 'hostname_test'


class TestGetSplunkdUri(ut.TestCase):

    def setUp(self):
        self._Popen_backup = subprocess.Popen
        subprocess.Popen = _MockPopen

    def tearDown(self):
        subprocess.Popen = self._Popen_backup

    def test_splunkhome_path(self):
        self.assertEqual(splunkenv.make_splunkhome_path(['etc', 'apps']),
                         os.environ['SPLUNK_HOME'] + 'etc/apps')

    def test_get_splunk_host_info(self):
        # Save origin gethostbyaddr
        gethostname_backup = socket.gethostname
        socket.gethostname = _mock_gethostname

        server_name, host_name = splunkenv.get_splunk_host_info()
        self.assertEqual(server_name, 'servername_test')
        self.assertEqual(host_name, 'hostname_test')

        socket.gethostname = gethostname_backup

    def test_splunk_bin(self):
        splunk_bin = splunkenv.get_splunk_bin()
        self.assertTrue(splunk_bin in (
            os.environ['SPLUNK_HOME'] + 'bin/splunk',
            os.environ['SPLUNK_HOME'] + 'bin/splunk.exe'))

    def test_get_splunkd_access_info(self):
        scheme, host, port = splunkenv.get_splunkd_access_info()
        self.assertEqual(scheme, 'https')
        self.assertEqual(host, '127.0.0.1')
        self.assertEqual(port, 8089)

    # Testcase depends on SPLUNK_HOME env variables
    def test_splunkd_uri(self):
        uri = splunkenv.get_splunkd_uri()
        self.assertEquals(uri, 'https://127.0.0.1:8089')

        os.environ['SPLUNKD_URI'] = 'https://10.0.0.1:8089'
        uri = splunkenv.get_splunkd_uri()
        self.assertEquals(uri, 'https://10.0.0.1:8089')
        del os.environ['SPLUNKD_URI']

        os.environ['SPLUNK_BINDIP'] = '10.0.0.2:7080'
        uri = splunkenv.get_splunkd_uri()
        self.assertEquals(uri, 'https://10.0.0.2:8089')
        del os.environ['SPLUNK_BINDIP']

        os.environ['SPLUNK_BINDIP'] = '10.0.0.3'
        uri = splunkenv.get_splunkd_uri()
        self.assertEquals(uri, 'https://10.0.0.3:8089')
        del os.environ['SPLUNK_BINDIP']

if __name__ == '__main__':
    ut.main(verbosity=2)
