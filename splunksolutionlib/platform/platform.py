# Copyright 2016 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Splunk platform related utilities.
"""

import os
import os.path as op
import subprocess
from ConfigParser import ConfigParser
from cStringIO import StringIO

import splunksolutionlib.common.utils as utils


def make_splunkhome_path(parts):
    """Construct absolute path by $SPLUNK_HOME and `parts`.

    Concatenate $SPLUNK_HOME and `parts` to an absolute path.
    For example, `parts` is ["etc", "apps", "Splunk_TA_test"],
    the return path will be $SPLUNK_HOME/etc/apps/Splunk_TA_test.
    Note: this function assumed SPLUNK_HOME is in environment varialbes.

    :param parts: Path parts
    :type parts: list, tuple
    :returns: Absolute path
    :rtype: str

    :raises KeyError: If $SPLUNK_HOME has not been set
    :raises ValueError: Escape from intended parent directories
    """

    assert parts is not None and isinstance(parts, (list, tuple)), \
        ValueError('Invalid path parts: %s' % parts)

    # Assume SPLUNK_HOME env has been set
    basepath = os.environ['SPLUNK_HOME']

    relpath = os.path.normpath(os.path.join(*parts))
    fullpath = os.path.normpath(os.path.join(basepath, relpath))

    # Check that we haven't escaped from intended parent directories.
    if os.path.relpath(fullpath, basepath)[0:2] == '..':
        raise ValueError('Illegal escape from parent directory "%s": %s' %
                         (basepath, fullpath))

    return fullpath


def get_splunk_bin():
    """Get absolute path of splunk CLI.

    :returns: absolute path of splunk CLI
    :rtype: str
    """

    if os.name == 'nt':
        splunk_bin = 'splunk.exe'
    else:
        splunk_bin = 'splunk'
    return make_splunkhome_path(('bin', splunk_bin))


def _get_merged_conf_raw(conf_name):
    """Get merged raw content of `conf_name`

    :param conf_name: Configure file name
    :returns: Merged raw content of `conf_name`
    :rtype: str

    :raises ValueError: If fail to get merged raw content
    """

    assert conf_name, ValueError('conf_name is None')

    if conf_name.endswith('.conf'):
        conf_name = conf_name[:-5]

    # TODO: dynamically caculate SPLUNK_HOME
    btool_cli = [op.join(os.environ['SPLUNK_HOME'], 'bin', 'btool'), conf_name,
                 'list']
    try:
        p = subprocess.Popen(btool_cli,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
    except OSError:
        raise

    return out


def _get_conf_stanzas(conf_name):
    """Get stanzas of `conf_name`

    :param conf_name: Configure file name
    :returns: Config stanzas like: {stanza_name: stanza_configs}
    :rtype: dict

    :raises ValueError: If fail to get merged raw content
    """

    res = _get_merged_conf_raw(conf_name)
    res = StringIO(res)
    parser = ConfigParser()
    parser.optionxform = str
    parser.readfp(res)
    res = {}
    for section in parser.sections():
        res[section] = {item[0]: item[1] for item in parser.items(section)}
    return res


def get_splunkd_uri():
    """Get splunkd uri.

    Construct splunkd uri by parsing web.conf and server.conf.

    :returns: Splunkd uri
    :rtype: str
    """

    if os.environ.get('SPLUNKD_URI'):
        return os.environ['SPLUNKD_URI']

    server_conf = _get_conf_stanzas('server')

    if utils.is_true(server_conf['sslConfig']['enableSplunkdSSL']):
        http = 'https://'
    else:
        http = 'http://'

    web_conf = _get_conf_stanzas('web')
    host_port = web_conf['settings']['mgmtHostPort']
    splunkd_uri = '{http}{host_port}'.format(http=http, host_port=host_port)

    if os.environ.get('SPLUNK_BINDIP'):
        bindip = os.environ['SPLUNK_BINDIP']
        port_idx = bindip.rfind(':')
        if port_idx > 0:
            bindip = bindip[:port_idx]
        port = host_port[host_port.rfind(':'):]
        splunkd_uri = '{http}{bindip}{port}'.format(
            http=http, bindip=bindip, port=port)
    return splunkd_uri
