#
# Copyright 2024 Splunk Inc.
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
import common
import pytest
from splunklib import binding

from solnlib import credentials


def test_get_session_key(monkeypatch):
    def _mock_session_key_post(self, url, headers=None, **kwargs):
        return common.make_response_record(
            '{"sessionKey":"' + common.SESSION_KEY + '"}'
        )

    common.mock_splunkhome(monkeypatch)
    monkeypatch.setattr(binding.HttpLib, "post", _mock_session_key_post)

    assert credentials.get_session_key("user", "password") == common.SESSION_KEY

    with pytest.raises(ValueError):
        credentials.get_session_key("user", "password", scheme="non-http")
    credentials.get_session_key("user", "password", scheme="http")
    credentials.get_session_key("user", "password", scheme="https")
    with pytest.raises(ValueError):
        credentials.get_session_key("user", "password", scheme="http", host="==")
    credentials.get_session_key("user", "password", scheme="http", host="localhost")
    with pytest.raises(ValueError):
        credentials.get_session_key(
            "user", "password", scheme="http", host="localhost", port=-10
        )
    credentials.get_session_key(
        "user", "password", scheme="http", host="localhost", port=10
    )
    credentials.get_session_key("user", "password", scheme="HTTP")
    credentials.get_session_key("user", "password", scheme="HTTPS")
