import logging
from solnlib import splunk_rest_client as rest_client
from splunklib import binding
import json


__all__ = ["BulletinRestClient"]


class BulletinRestClient:
    READ_ENDPOINT = "/services/admin/messages"
    CREATE_DELETE_ENDPOINT = "/services/messages"

    headers = [("Content-Type", "application/json")]

    def __init__(
        self,
        message_name: str,
        session_key: str,
        logger: logging.Logger = None,
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
        self.logger.info(f"mymy123 init {self.message_name}")

    def create_message(self, msg):
        body = {"name": self.message_name, "value": msg}
        self.logger.info(f"mymy123 create_message {self.message_name} {msg}")
        try:
            self._rest_client.post(
                self.CREATE_DELETE_ENDPOINT, body=body, headers=self.headers
            )
        except binding.HTTPError as e:
            if 400 <= e.status < 500:
                self.logger.error(
                    f"Create message failed - {e.status} "
                    f"Client Error: {e.reason} for url: {self.CREATE_DELETE_ENDPOINT}"
                )
            if 500 <= e.status < 600:
                self.logger.error(
                    f"Create message failed - {e.status} "
                    f"Server Error: {e.reason} for url: {self.CREATE_DELETE_ENDPOINT}"
                )

    def get_message(self):
        endpoint = f"{self.READ_ENDPOINT}/{self.message_name}"
        self.logger.info(f"mymy123 get_message {self.message_name} url {endpoint}")
        try:
            response = self._rest_client.get(endpoint, output_mode="json").body.read()
            return json.loads(response)
        except binding.HTTPError as e:
            if 400 <= e.status < 500:
                self.logger.error(
                    f"Get message failed - {e.status} Client Error: {e.reason} for url: {endpoint}"
                )
            if 500 <= e.status < 600:
                self.logger.error(
                    f"Get message failed - {e.status} Server Error: {e.reason} for url: {endpoint}"
                )

    def get_all_messages(self):
        self.logger.info(
            f"mymy123 get all message {self.message_name} url {self.READ_ENDPOINT}"
        )
        try:
            response = self._rest_client.get(
                self.READ_ENDPOINT, output_mode="json"
            ).body.read()
            return json.loads(response)
        except binding.HTTPError as e:
            if 400 <= e.status < 500:
                self.logger.error(
                    f"Get all messages failed - {e.status} Client Error: {e.reason} for url: {self.READ_ENDPOINT}"
                )
            if 500 <= e.status < 600:
                self.logger.error(
                    f"Get all messages failed - {e.status} Server Error: {e.reason} for url: {self.READ_ENDPOINT}"
                )

    def delete_message(self):
        endpoint = f"{self.CREATE_DELETE_ENDPOINT}/{self.message_name}"
        self.logger.info(f"mymy123 delete message {self.message_name} url {endpoint}")
        try:
            self._rest_client.delete(endpoint)
        except binding.HTTPError as e:
            if 400 <= e.status < 500:
                self.logger.error(
                    f"Delete message failed - {e.status} Client Error: {e.reason} for url: {endpoint}"
                )
            if 500 <= e.status < 600:
                self.logger.error(
                    f"Delete message failed - {e.status} Server Error: {e.reason} for url: {endpoint}"
                )
