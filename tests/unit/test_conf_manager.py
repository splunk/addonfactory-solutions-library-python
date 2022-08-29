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

from solnlib import conf_manager


@mock.patch.object(conf_manager, "ConfManager")
def test_get_log_level_when_error_getting_conf(mock_conf_manager_class):
    mock_conf_manager = mock_conf_manager_class.return_value
    mock_conf_manager.get_conf.side_effect = conf_manager.ConfManagerException
    expected_log_level = "INFO"

    log_level = conf_manager.get_log_level(
        logger=mock.MagicMock(),
        session_key="session_key",
        app_name="app_name",
        conf_name="conf_name",
    )

    assert expected_log_level == log_level
