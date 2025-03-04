#
# Copyright 2025 Splunk Inc.
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

import context
import pytest
import solnlib
from time import sleep
from splunklib import binding
from solnlib import splunk_rest_client as rest_client

from _search import search


def test_rest_client_user_agent():
    test_url = r'search index = _internal uri_path="*/servicesNS/nobody/test_app/some/unexisting/url"'
    user_agent = f"solnlib/{solnlib.__version__} rest-client linux"
    session_key = context.get_session_key()
    wrong_url = r"some/unexisting/url"
    rc = rest_client.SplunkRestClient(
        session_key,
        app="test_app",
        owner=context.owner,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )
    with pytest.raises(binding.HTTPError):
        rc.get(wrong_url)

    for i in range(50):
        search_results = search(session_key, test_url)
        if len(search_results) > 0:
            break
        sleep(0.5)

    assert user_agent in search_results[0]["_raw"]
