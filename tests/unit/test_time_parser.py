#
# Copyright 2021 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from unittest import mock

import common
import pytest
from splunklib import binding

from solnlib import time_parser


@mock.patch("solnlib.splunk_rest_client.SplunkRestClient")
def test_to_seconds_raises_error_when_rest_client_responds_with_503_status(
    mock_splunk_rest_client_class,
):
    mock_splunk_rest_client_object = mock_splunk_rest_client_class.return_value
    mock_splunk_rest_client_object.get.side_effect = binding.HTTPError(
        common.make_response_record(b"", status=503)
    )
    tp = time_parser.TimeParser("session_key")
    with pytest.raises(binding.HTTPError):
        tp.to_seconds("2011-07-06T21:54:23.000-07:00")


@mock.patch("solnlib.splunk_rest_client.SplunkRestClient")
def test_to_utc_raises_error_when_rest_client_responds_with_503_status(
    mock_splunk_rest_client_class,
):
    mock_splunk_rest_client_object = mock_splunk_rest_client_class.return_value
    mock_splunk_rest_client_object.get.side_effect = binding.HTTPError(
        common.make_response_record(b"", status=503)
    )
    tp = time_parser.TimeParser("session_key")
    with pytest.raises(binding.HTTPError):
        tp.to_utc("2011-07-06T21:54:23.000-07:00")


@mock.patch("solnlib.splunk_rest_client.SplunkRestClient")
def test_to_local_raises_error_when_rest_client_responds_with_503_status(
    mock_splunk_rest_client_class,
):
    mock_splunk_rest_client_object = mock_splunk_rest_client_class.return_value
    mock_splunk_rest_client_object.get.side_effect = binding.HTTPError(
        common.make_response_record(b"", status=503)
    )
    tp = time_parser.TimeParser("session_key")
    with pytest.raises(binding.HTTPError):
        tp.to_local("2011-07-06T21:54:23.000-07:00")
