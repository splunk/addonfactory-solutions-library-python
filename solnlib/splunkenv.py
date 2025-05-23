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

"""Splunk platform related utilities."""

import os
import os.path as op
import socket
import subprocess
import json
from configparser import ConfigParser
from io import StringIO
from typing import List, Optional, Tuple, Union

from splunk.clilib.bundle_paths import make_splunkhome_path as msp
from splunk.rest import simpleRequest
from splunk import getSessionKey

from .utils import is_true

__all__ = [
    "make_splunkhome_path",
    "get_splunk_host_info",
    "get_splunk_bin",
    "get_splunkd_access_info",
    "get_scheme_from_hec_settings",
    "get_splunkd_uri",
    "get_conf_key_value",
    "get_conf_stanza",
    "get_conf_stanzas",
    "_get_conf_stanzas_from_splunk_api",
]

ETC_LEAF = "etc"
APP_SYSTEM = "system"
APP_HEC = "splunk_httpinput"

# See validateSearchHeadPooling() in src/libbundle/ConfSettings.cpp
on_shared_storage = [
    os.path.join(ETC_LEAF, "apps"),
    os.path.join(ETC_LEAF, "users"),
    os.path.join("var", "run", "splunk", "dispatch"),
    os.path.join("var", "run", "splunk", "srtemp"),
    os.path.join("var", "run", "splunk", "rss"),
    os.path.join("var", "run", "splunk", "scheduler"),
    os.path.join("var", "run", "splunk", "lookup_tmp"),
]


def make_splunkhome_path(parts: Union[List, Tuple]) -> str:
    """Construct absolute path by $SPLUNK_HOME and `parts`.

    Concatenate $SPLUNK_HOME and `parts` to an absolute path.
    For example, `parts` is ['etc', 'apps', 'Splunk_TA_test'],
    the return path will be $SPLUNK_HOME/etc/apps/Splunk_TA_test.
    Note: this function assumed SPLUNK_HOME is in environment varialbes.

    Arguments:
        parts: Path parts.

    Returns:
        Absolute path.

    Raises:
        ValueError: Escape from intended parent directories.
    """
    return msp(parts)


def get_splunk_host_info(
    use_btool: Optional[bool] = False, session_key: Optional[str] = None
) -> Tuple:
    """Get splunk host info.

    Returns:
        Tuple of (server_name, host_name).
    """

    server_name = get_conf_key_value(
        "server",
        "general",
        "serverName",
        use_btool=use_btool,
        session_key=session_key,
        app_name=APP_SYSTEM,
    )
    host_name = socket.gethostname()

    return server_name, host_name


def get_splunk_bin() -> str:
    """Get absolute path of splunk CLI.

    Returns:
        Absolute path of splunk CLI.
    """

    if os.name == "nt":
        splunk_bin = "splunk.exe"
    else:
        splunk_bin = "splunk"
    return make_splunkhome_path(("bin", splunk_bin))


def get_splunkd_access_info(
    use_btool: Optional[bool] = False, session_key: Optional[str] = None
) -> Tuple[str, str, int]:
    """Get splunkd server access info.

    Returns:
        Tuple of (scheme, host, port).
    """
    enable_splunkd_ssl = get_conf_key_value(
        "server",
        "sslConfig",
        "enableSplunkdSSL",
        use_btool=use_btool,
        session_key=session_key,
        app_name=APP_SYSTEM,
    )

    if is_true(enable_splunkd_ssl):
        scheme = "https"
    else:
        scheme = "http"

    host_port = get_conf_key_value(
        "web",
        "settings",
        "mgmtHostPort",
        use_btool=use_btool,
        session_key=session_key,
        app_name=APP_SYSTEM,
    )
    host_port = host_port.strip()
    host_port_split_parts = host_port.split(":")
    host = ":".join(host_port_split_parts[:-1])
    port = int(host_port_split_parts[-1])

    if "SPLUNK_BINDIP" in os.environ:
        bindip = os.environ["SPLUNK_BINDIP"]
        port_idx = bindip.rfind(":")
        host = bindip[:port_idx] if port_idx > 0 else bindip

    return scheme, host, port


def get_scheme_from_hec_settings(
    use_btool: Optional[bool] = False, session_key: Optional[str] = None
) -> str:
    """Get scheme from HEC global settings.

    Returns:
        scheme (str)
    """
    try:
        ssl_enabled = get_conf_key_value(
            "inputs",
            "http",
            "enableSSL",
            use_btool=use_btool,
            session_key=session_key,
            app_name=APP_HEC,
        )
    except KeyError:
        raise KeyError(
            "Cannot get enableSSL setting form conf: 'inputs' and stanza: '[http]'. "
            "Verify that your Splunk instance has the inputs.conf file with the correct [http] stanza. "
            "For more information see: "
            "https://docs.splunk.com/Documentation/Splunk/9.2.0/Data/UseHECusingconffiles"
        )

    if is_true(ssl_enabled):
        scheme = "https"
    else:
        scheme = "http"

    return scheme


def get_splunkd_uri() -> str:
    """Get splunkd uri.

    Returns:
        Splunkd uri.
    """

    if os.environ.get("SPLUNKD_URI"):
        return os.environ["SPLUNKD_URI"]

    scheme, host, port = get_splunkd_access_info(use_btool=True)
    return f"{scheme}://{host}:{port}"


def get_conf_key_value(
    conf_name: str,
    stanza: str,
    key: str,
    use_btool: Optional[bool] = False,
    app_name: Optional[str] = None,
    session_key: Optional[str] = None,
    user: Optional[str] = "nobody",
) -> Union[str, List, dict]:
    """Get value of `key` of `stanza` in `conf_name`.

    Arguments:
        conf_name: Config file.
        stanza: Stanza name.
        key: Key name.
        use_btool: If True, stanzas will be retrieved using cmd btool... otherwise using splunk API. Optional.
        app_name: Application name. Optional.
        session_key: If not provided solnlib will try to get it from splunk.getSessionKey(). Optional.
        user: used for set user context in API call. Optional.

    Returns:
        Config value.

    Raises:
        KeyError: If `stanza` or `key` doesn't exist.
    """

    if use_btool:
        stanzas = get_conf_stanzas(conf_name, app_name)
        return stanzas[stanza][key]

    if not app_name:
        raise KeyError("app name must be specified if use_btool is True")

    stanzas = _get_conf_stanzas_from_splunk_api(
        conf_name, app_name, session_key=session_key, user=user, stanza=stanza
    )

    stanza = stanzas.get("entry")[0].get("content")
    requested_key = stanza[key]
    return requested_key


def get_conf_stanza(
    conf_name: str,
    stanza: str,
    use_btool: Optional[bool] = False,
    app_name: Optional[str] = None,
    session_key: Optional[str] = None,
    user: Optional[str] = "nobody",
) -> dict:
    """Get `stanza` in `conf_name`.

    Arguments:
        conf_name: Config file.
        stanza: Stanza name.
        use_btool: If True, stanzas will be retrieved using cmd btool... otherwise using splunk API. Optional.
        app_name: Application name. Optional.
        session_key: If not provided solnlib will try to get it from splunk.getSessionKey(). Optional.
        user: used for set user context in API call. Optional.
        app_name: Application name. Optional.

    Returns:
        Config stanza.

    Raises:
         KeyError: If stanza doesn't exist.
    """

    if use_btool:
        stanzas = get_conf_stanzas(conf_name, app_name)
        return stanzas[stanza]  # uncomment after tests

    if not app_name:
        raise KeyError("app name must be specified if use_btool is True")

    stanzas = _get_conf_stanzas_from_splunk_api(
        conf_name, app_name, session_key=session_key, user=user, stanza=stanza
    )

    stanza = stanzas.get("entry")[0].get("content")
    return stanza


def get_conf_stanzas(conf_name: str, app_name: Optional[str] = None) -> dict:
    """Get stanzas of `conf_name`

    Arguments:
        conf_name: Config file.
        app_name: Application name. Optional.

    Returns:
        Config stanzas.

    Examples:
       >>> stanzas = get_conf_stanzas('server')
       >>> return: {'serverName': 'testServer', 'sessionTimeout': '1h', ...}
    """

    if conf_name.endswith(".conf"):
        conf_name = conf_name[:-5]

    # TODO: dynamically calculate SPLUNK_HOME
    btool_cli = [
        op.join(os.environ["SPLUNK_HOME"], "bin", "splunk"),
        "cmd",
        "btool",
        conf_name,
        "list",
    ]

    if app_name:
        btool_cli.append(f"--app={app_name}")

    p = subprocess.Popen(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use.dangerous-subprocess-use
        btool_cli, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, _ = p.communicate()

    if isinstance(out, bytes):
        out = out.decode()

    parser = ConfigParser(**{"strict": False})
    parser.optionxform = str
    parser.read_file(StringIO(out))

    out = {}
    for section in parser.sections():
        out[section] = {item[0]: item[1] for item in parser.items(section, raw=True)}
    return out


def _get_conf_stanzas_from_splunk_api(
    conf_name: str,
    app_name: str,
    session_key: Optional[str] = None,
    user: Optional[str] = "nobody",
    stanza: Optional[str] = None,
) -> dict:
    """Get stanzas of `conf_name` using splunk API:

    /servicesNS/{user}/{app_name}/configs/conf-{conf_name}/{stanza}

    Arguments:
        conf_name: Config file.
        app_name: Application name.
        session_key: Session key. Optional.
        user: Username. Optional.
        stanza: Stanza name. Optional.

    Returns:
        json response.
    """

    url = f"/servicesNS/{user}/{app_name}/configs/conf-{conf_name}"

    if stanza:
        url = url + "/" + stanza

    if not session_key:
        session_key = getSessionKey()

    server_response, server_content = simpleRequest(
        url, sessionKey=session_key, getargs={"output_mode": "json"}, logme=True
    )

    result = json.loads(server_content.decode())

    return result
