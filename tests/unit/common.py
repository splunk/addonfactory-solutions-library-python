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

import os
import os.path as op
import socket

from configparser import ConfigParser
from io import StringIO

from splunklib import binding, client
from splunklib.data import record

cur_dir = op.dirname(op.abspath(__file__))

# Namespace
app = "unittest"
owner = "nobody"

# Session key sample
SESSION_KEY = "nU1aB6BntzwREOnGowa7pN6avV3B6JefliAZIzCX9"


def mock_splunkhome(monkeypatch):
    def get_app_conf(confName, app, use_btool, app_path):
        if confName == "server":
            file_path = op.sep.join(
                [cur_dir, "data/mock_splunk/etc/system/default/server.conf"]
            )
        elif confName == "inputs":
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
            data = fp.read(), None

        parser = ConfigParser(**{"strict": False})
        parser.optionxform = str
        parser.read_file(StringIO(data[0]))

        out = {}
        for section in parser.sections():
            out[section] = {
                item[0]: item[1] for item in parser.items(section, raw=True)
            }
        return out

    def make_splunk_gome(parts):
        relpath = os.path.normpath(os.path.join(*parts))
        basepath = ""
        etc_with_trailing_sep = os.path.join("etc", "")
        if (relpath == "etc") or relpath.startswith(etc_with_trailing_sep):
            try:
                basepath = os.environ["SPLUNK_ETC"]
            except KeyError:
                basepath = op.join(os.path.normpath(os.environ["SPLUNK_HOME"]), "etc")
            relpath = relpath[4:]
        else:
            basepath = os.path.normpath(os.environ["SPLUNK_HOME"])
        fullpath = os.path.normpath(os.path.join(basepath, relpath))
        if os.path.relpath(fullpath, basepath)[0:2] == "..":
            raise ValueError(
                'Illegal escape from parent directory "{}": {}'.format(
                    basepath, fullpath
                )
            )

        return fullpath

    splunk_home = op.join(cur_dir, "data/mock_splunk/")
    monkeypatch.setenv("SPLUNK_HOME", splunk_home)
    monkeypatch.setenv("SPLUNK_ETC", op.join(splunk_home, "etc"))
    monkeypatch.setattr("solnlib.splunkenv.getAppConf", get_app_conf)
    monkeypatch.setattr("solnlib.splunkenv.mksplhomepath", make_splunk_gome)


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
