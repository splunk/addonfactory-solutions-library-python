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

from solnlib import splunk_rest_client as rest_client
from splunklib import binding
from typing import Optional, List
import json

__all__ = ["BulletinRestClient"]


class BulletinRestClient:
    """REST client for handling Bulletin messages."""

    MESSAGES_ENDPOINT = "/services/messages"

    headers = [("Content-Type", "application/json")]

    class Severity:
        INFO = "info"
        WARNING = "warn"
        ERROR = "error"

    def __init__(
        self,
        message_name: str,
        session_key: str,
        **context: dict,
    ):
        """Initializes BulletinRestClient.

            One instance is responsible for handling one, particular message.
            If you need to add another message to bulletin create another instance
            with a different 'message_name'
            e.g.
            msg_1 = BulletinRestClient("message_1", "<some session key>")
            msg_2 = BulletinRestClient("message_2", "<some session key>")

        Arguments:
            message_name: Name of the message in the splunk's bulletin.
            session_key: Splunk access token.
            context: Other configurations for Splunk rest client.
        """

        self.message_name = message_name
        self.session_key = session_key

        self._rest_client = rest_client.SplunkRestClient(
            self.session_key, app="-", **context
        )

    def create_message(
        self,
        msg: str,
        severity: Severity = Severity.WARNING,
        capabilities: Optional[List[str]] = None,
        roles: Optional[List] = None,
    ):
        """Creates a message in the splunk's bulletin.' Calling this method
        multiple times for the same instance will overwrite existing message.

        Arguments:
            msg: The message which will be displayed in the splunk's bulletin'
            severity: Severity level of the message. It has to be one of: 'info', 'warn', 'error'.
            If wrong severity is given, ValueError will be raised.
            capabilities: One or more capabilities that users must have to view the message.
                Capability names are validated.
                This argument should be provided as a list of string/s e.g. capabilities=['one', 'two'].
                If a non-existent capability is used, HTTP 400 BAD REQUEST exception will be raised.
                If argument is not a List[str] ValueError will be raised.
            roles: One or more roles that users must have to view the message. Role names are validated.
                This argument should be provided as a list of string/s e.g. roles=['user', 'admin'].
                If a non-existent role is used, HTTP 400 BAD REQUEST exception will be raised.
                If argument is not a List[str] ValueError will be raised.
        """
        body = {
            "name": self.message_name,
            "value": msg,
            "severity": severity,
            "capability": [],
            "role": [],
        }

        if severity not in ("info", "warn", "error"):
            raise ValueError("Severity must be one of ('info', 'warn', 'error').")

        if capabilities:
            body["capability"] = self._validate_and_get_body_value(
                capabilities, "Capabilities must be a list of strings."
            )

        if roles:
            body["role"] = self._validate_and_get_body_value(
                roles, "Roles must be a list of strings."
            )

        try:
            self._rest_client.post(
                self.MESSAGES_ENDPOINT, body=body, headers=self.headers
            )
        except binding.HTTPError:
            raise

    def get_message(self):
        """Get specific message created by this instance."""
        endpoint = f"{self.MESSAGES_ENDPOINT}/{self.message_name}"
        response = self._rest_client.get(endpoint, output_mode="json").body.read()
        return json.loads(response)

    def get_all_messages(self):
        """Get all messages in the bulletin."""
        response = self._rest_client.get(
            self.MESSAGES_ENDPOINT, output_mode="json"
        ).body.read()
        return json.loads(response)

    def delete_message(self):
        """Delete specific message created by this instance."""
        endpoint = f"{self.MESSAGES_ENDPOINT}/{self.message_name}"
        self._rest_client.delete(endpoint)

    @staticmethod
    def _validate_and_get_body_value(arg, error_msg) -> List:
        if type(arg) is list and (all(isinstance(el, str) for el in arg)):
            return [el for el in arg]
        else:
            raise ValueError(error_msg)
