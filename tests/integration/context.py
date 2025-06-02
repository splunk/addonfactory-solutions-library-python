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
from urllib import parse

import requests

owner = "nobody"
app = "solnlib_demo"

username = "admin"
password = "Chang3d!"
scheme = "https"
host = "localhost"
port = 8089


def get_session_key():
    response = requests.post(
        f"{scheme}://{host}:{port}/services/auth/login?output_mode=json",
        data=parse.urlencode({"username": username, "password": password}),
        verify=False,
    )
    content = response.json()
    return content["sessionKey"]


def mock_splunk(monkeypatch):
    def simple_requests(url, *args, **kwargs):
        from splunk.rest import simpleRequest

        return simpleRequest(url, *args, **kwargs)

    def make_splunkn_home(url, *args, **kwargs):
        from splunk.clilib.bundle_paths import make_splunkhome_path

        return make_splunkhome_path(url, *args, **kwargs)

    monkeypatch.setattr("solnlib.splunkenv.simpleRequest", simple_requests)
    monkeypatch.setattr("solnlib.splunkenv.msp", make_splunkn_home)
