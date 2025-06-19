#
# Copyright 2023 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os.path as op
import socket
import subprocess

from splunklib import binding, client
from splunklib.data import record

cur_dir = op.dirname(op.abspath(__file__))

# Namespace
app = "unittest"
owner = "nobody"

# Session key sample
SESSION_KEY = "nU1aB6BntzwREOnGowa7pN6avV3B6JefliAZIzCX9"


def mock_splunkhome(monkeypatch):
    class MockPopen:
        def __init__(
            self,
            args,
            bufsize=0,
            executable=None,
            stdin=None,
            stdout=None,
            stderr=None,
            preexec_fn=None,
            close_fds=False,
            shell=False,
            cwd=None,
            env=None,
            universal_newlines=False,
            startupinfo=None,
            creationflags=0,
        ):
            self._conf = args[3]

        def communicate(self, input=None):
            if self._conf == "server":
                file_path = op.sep.join(
                    [cur_dir, "data/mock_splunk/etc/system/default/server.conf"]
                )
            elif self._conf == "inputs":
                file_path = op.sep.join(
                    [
                        cur_dir,
                        "data/mock_splunk/etc/apps/splunk_httpinput/local/inputs.conf",
                    ]
                )
            else:
                file_path = op.sep.join(
                    [cur_dir, "data/mock_splunk/etc/system/default/web.conf"]
                )

            with open(file_path) as fp:
                return fp.read(), None

    def simple_requests(url, *args, **kwargs):
        if "conf-server/sslConfig" in url:
            file_path = op.sep.join(
                [cur_dir, "data/mock_splunk/etc/system/default/server-sslconfig.json"]
            )
        elif "conf-server/general" in url:
            file_path = op.sep.join(
                [cur_dir, "data/mock_splunk/etc/system/default/server-general.json"]
            )
        elif "conf-inputs" in url:
            file_path = op.sep.join(
                [
                    cur_dir,
                    "data/mock_splunk/etc/apps/splunk_httpinput/local/inputs.json",
                ]
            )
        else:
            file_path = op.sep.join(
                [cur_dir, "data/mock_splunk/etc/system/default/web.json"]
            )
        with open(file_path) as fp:
            data = fp.read(), None

        out = data[0]
        return "200", out.encode("utf8")

    def get_session_key():
        return None

    splunk_home = op.join(cur_dir, "data/mock_splunk/")
    monkeypatch.setenv("SPLUNK_HOME", splunk_home)
    monkeypatch.setenv("SPLUNK_ETC", op.join(splunk_home, "etc"))
    monkeypatch.setattr("solnlib.splunkenv.simpleRequest", simple_requests)
    monkeypatch.setattr("solnlib.splunkenv.getSessionKey", get_session_key)
    monkeypatch.setattr(subprocess, "Popen", MockPopen)


def mock_serverinfo(monkeypatch):
    mock_server_info_property = {
        "server_roles": [
            "cluster_search_head",
            "search_head",
            "kv_store",
            "shc_captain",
        ],
        "version": "6.3.1511.2",
        "serverName": "unittestServer",
    }

    monkeypatch.setattr(client.Service, "info", mock_server_info_property)


def mock_gethostname(monkeypatch):
    def mock_gethostname():
        return "unittestServer"

    monkeypatch.setattr(socket, "gethostname", mock_gethostname)


def make_response_record(body, status=200):
    class _MocBufReader:
        def __init__(self, buf):
            if isinstance(buf, str):
                self._buf = buf.encode("utf-8")
            else:
                self._buf = buf

        def read(self, size=None):
            return self._buf

    return record(
        {
            "body": binding.ResponseReader(_MocBufReader(body)),
            "status": status,
            "reason": "",
            "headers": None,
        }
    )
