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

import logging
from solnlib import splunk_rest_client as rest_client
from splunklib import binding
from typing import Optional
import json


__all__ = ["BulletinRestClient"]


class BulletinRestClient:
    READ_ENDPOINT = "/services/admin/messages"
    CREATE_DELETE_ENDPOINT = "/services/messages"

    headers = [("Content-Type", "application/json")]

    class LogLevel:
        INFO = "info"
        WARNING = "warn"
        ERROR = "error"

    def __init__(
        self,
        message_name: str,
        session_key: str,
        logger: Optional[logging.Logger] = None,
        **context: dict,
    ):

        self.message_name = message_name
        self.session_key = session_key

        if logger:
            self.logger = logger
        else:
            self.logger = logging

        self._rest_client = rest_client.SplunkRestClient(
            self.session_key, app="-", **context
        )

    def create_message(self, msg, msg_lvl=LogLevel.WARNING):
        body = {"name": self.message_name, "value": msg, "severity": msg_lvl}
        try:
            self._rest_client.post(
                self.CREATE_DELETE_ENDPOINT, body=body, headers=self.headers
            )
        except binding.HTTPError:
            raise

    def get_message(self):
        endpoint = f"{self.READ_ENDPOINT}/{self.message_name}"
        try:
            response = self._rest_client.get(endpoint, output_mode="json").body.read()
            return json.loads(response)
        except binding.HTTPError:
            raise

    def get_all_messages(self):
        try:
            response = self._rest_client.get(
                self.READ_ENDPOINT, output_mode="json"
            ).body.read()
            return json.loads(response)
        except binding.HTTPError:
            raise

    def delete_message(self):
        endpoint = f"{self.CREATE_DELETE_ENDPOINT}/{self.message_name}"
        try:
            self._rest_client.delete(endpoint)
        except binding.HTTPError:
            raise
