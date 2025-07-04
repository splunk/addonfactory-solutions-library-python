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

"""This module proxy all REST call to splunklib SDK, it handles proxy, certs
etc in this centralized location.

All clients should use SplunkRestProxy to do REST call instead of
calling splunklib SDK directly in business logic code.
"""

import logging
import os
import sys
import traceback
import solnlib

from io import BytesIO
from urllib.parse import quote
from urllib3.util.retry import Retry
from splunklib import binding, client

from .net_utils import validate_scheme_host_port
from .splunkenv import get_splunkd_access_info

__all__ = ["SplunkRestClient"]
MAX_REQUEST_RETRIES = 5


def _get_proxy_info(context):
    if not context.get("proxy_hostname") or not context.get("proxy_port"):
        return None

    user_pass = ""
    if context.get("proxy_username") and context.get("proxy_password"):
        username = quote(context["proxy_username"], safe="")
        password = quote(context["proxy_password"], safe="")
        user_pass = f"{username}:{password}@"

    proxy = "http://{user_pass}{host}:{port}".format(
        user_pass=user_pass, host=context["proxy_hostname"], port=context["proxy_port"]
    )
    proxies = {
        "http": proxy,
        "https": proxy,
    }
    return proxies


def _request_handler(context):
    """
    :param context: Http connection context can contain the following
        key/values: {
        'proxy_hostname': string,
        'proxy_port': int,
        'proxy_username': string,
        'proxy_password': string,
        'key_file': string,
        'cert_file': string
        'pool_connections', int,
        'pool_maxsize', int,
        }
    :type content: dict
    """

    try:
        import requests
    except ImportError:
        # FIXME proxy ?
        return binding.handler(
            key_file=context.get("key_file"), cert_file=context.get("cert_file")
        )

    try:
        requests.urllib3.disable_warnings()
    except AttributeError:
        pass

    proxies = _get_proxy_info(context)
    verify = context.get("verify", False)

    if context.get("key_file") and context.get("cert_file"):
        # cert: if tuple, ('cert', 'key') pair as per requests library
        cert = context["cert_file"], context["key_file"]
    elif context.get("cert_file"):
        cert = context["cert_file"]
    elif context.get("cert"):
        # as the solnlib uses requests, we need to have a check for 'cert' key as well
        cert = context["cert"]
    else:
        cert = None

    retries = Retry(
        total=MAX_REQUEST_RETRIES,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE"],
        raise_on_status=False,
    )
    if context.get("pool_connections", 0):
        logging.info("Use HTTP connection pooling")
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=retries,
            pool_connections=context.get("pool_connections", 10),
            pool_maxsize=context.get("pool_maxsize", 10),
        )
        session.mount("https://", adapter)
        req_func = session.request
    else:
        req_func = requests.request

    def request(url, message, **kwargs):
        """
        :param url: URL
        :type url: string
        :param message: Can contain following key/values: {
            'method': 'GET' or 'DELETE', or 'PUT' or 'POST'
            'headers': [[key, value], [key, value], ...],
            'body': string
            }
        :type message: dict
        """

        body = message.get("body")
        headers = {
            "User-Agent": f"solnlib/{solnlib.__version__} rest-client {sys.platform}",
            "Accept": "*/*",
            "Connection": "Keep-Alive",
        }

        if body:
            headers["Content-Length"] = str(len(body))

        for key, value in message["headers"]:
            headers[key] = value

        method = message.get("method", "GET")

        try:
            resp = req_func(
                method,
                url,
                data=body,
                headers=headers,
                stream=False,
                verify=verify,
                proxies=proxies,
                cert=cert,
                **kwargs,
            )
        except Exception:
            logging.error(
                "Failed to issue http request=%s to url=%s, error=%s",
                method,
                url,
                traceback.format_exc(),
            )
            raise

        return {
            "status": resp.status_code,
            "reason": resp.reason,
            "headers": dict(resp.headers),
            "body": BytesIO(resp.content),
        }

    return request


class SplunkRestClient(client.Service):
    """Splunk REST client."""

    def __init__(
        self,
        session_key: str,
        app: str,
        owner: str = "nobody",
        scheme: str = None,
        host: str = None,
        port: int = None,
        **context: dict,
    ):
        """Initializes SplunkRestClient.

        Arguments `scheme`, `host` and `port` are optional in the Splunk
        environment (when environment variable SPLUNK_HOME is set). In this
        situation `get_splunkd_access_info` will be used to set `scheme`,
        `host` and `port`. In case of using `SplunkRestClient` outside of
        Splunk environment - `scheme`, `host` and `port` should be provided.

        Arguments:
            session_key: Splunk access token.
            app: App name of namespace.
            owner: Owner of namespace, default is `nobody`.
            scheme: The access scheme, default is None.
            host: The host name, default is None.
            port: The port number, default is None.
            context: Other configurations, it can contain `proxy_hostname`,
                `proxy_port`, `proxy_username`, `proxy_password`, then proxy will
                be accounted and setup, all REST APIs to splunkd will be through
                the proxy. If `context` contains `key_file`, `cert_file`, then
                certification will be accounted and setup, all REST APIs to splunkd
                will use certification. If `context` contains `pool_connections`,
                `pool_maxsize`, then HTTP connection will be pooled.

        Raises:
            ValueError: if scheme, host or port are invalid.
        """
        # Only do splunkd URI discovery in SPLUNK env (SPLUNK_HOME is set).
        if not all([scheme, host, port]) and os.environ.get("SPLUNK_HOME"):
            scheme, host, port = get_splunkd_access_info(session_key)
        if os.environ.get("SPLUNK_HOME") is None:
            if not all([scheme, host, port]):
                raise ValueError(
                    "scheme, host, port should be provided outside of Splunk environment"
                )

        validate_scheme_host_port(scheme, host, port)
        if host == "[::1]":
            host = "::1"

        handler = _request_handler(context)
        super().__init__(
            handler=handler,
            scheme=scheme,
            host=host,
            port=port,
            token=session_key,
            app=app,
            owner=owner,
            autologin=True,
        )
