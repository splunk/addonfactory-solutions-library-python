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

'''
Splunk platform related utilities.
'''

import os
import os.path as op
import subprocess
import logging
from ConfigParser import ConfigParser
from cStringIO import StringIO

import splunksolutionlib.common.utils as utils

__all__ = ['make_splunkhome_path',
           'get_splunk_bin',
           'get_splunkd_serverinfo',
           'get_splunkd_uri']

ETC_LEAF = 'etc'

# See validateSearchHeadPooling() in src/libbundle/ConfSettings.cpp
on_shared_storage = [os.path.join(ETC_LEAF, 'apps'),
                     os.path.join(ETC_LEAF, 'users'),
                     os.path.join('var', 'run', 'splunk', 'dispatch'),
                     os.path.join('var', 'run', 'splunk', 'srtemp'),
                     os.path.join('var', 'run', 'splunk', 'rss'),
                     os.path.join('var', 'run', 'splunk', 'scheduler'),
                     os.path.join('var', 'run', 'splunk', 'lookup_tmp')]


def _splunk_home():
    return os.path.normpath(os.environ["SPLUNK_HOME"])


def _splunk_etc():
    try:
        result = os.environ['SPLUNK_ETC']
    except KeyError:
        result = op.join(_splunk_home, ETC_LEAF)
        logging.warn('SPLUNK_ETC is not defined; falling back to %s' % result)

    return os.path.normpath(result)


# Verify path prefix and return true if both paths have drives
def _verify_path_prefix(path, start):
    path_drive = os.path.splitdrive(path)[0]
    start_drive = os.path.splitdrive(start)[0]
    return len(path_drive) == len(start_drive)


def _get_shared_storage():
    server_conf = _get_conf_stanzas('server')
    try:
        state = server_conf['pooling']['state']
        storage = server_conf['pooling']['storage']
    except KeyError:
        state = 'disabled'
        storage = None

    if state == 'enabled' and storage:
        return storage

    return None


def make_splunkhome_path(parts):
    '''Construct absolute path by $SPLUNK_HOME and `parts`.

    Concatenate $SPLUNK_HOME and `parts` to an absolute path.
    For example, `parts` is ['etc', 'apps', 'Splunk_TA_test'],
    the return path will be $SPLUNK_HOME/etc/apps/Splunk_TA_test.
    Note: this function assumed SPLUNK_HOME is in environment varialbes.

    :param parts: Path parts.
    :type parts: ``list, tuple``
    :returns: Absolute path.
    :rtype: ``string``

    :raises ValueError: Escape from intended parent directories
    '''

    assert parts and isinstance(parts, (list, tuple)), \
        'parts is not a list or tuple: %r' % parts

    relpath = os.path.normpath(os.path.join(*parts))

    basepath = None
    shared_storage = _get_shared_storage()
    if shared_storage:
        for candidate in on_shared_storage:
            # SPL-100508 On windows if the path is missing the drive letter, construct fullpath manually and call relpath
            if os.name == 'nt' and not _verify_path_prefix(relpath, candidate):
                break

            if os.path.relpath(relpath, candidate)[0:2] != '..':
                basepath = shared_storage
                break

    if basepath is None:
        etc_with_trailing_sep = os.path.join(ETC_LEAF, '')
        if relpath == ETC_LEAF or relpath.startswith(etc_with_trailing_sep):
            # Redirect $SPLUNK_HOME/etc to $SPLUNK_ETC.
            basepath = _splunk_etc()
            # Remove leading etc (and path separator, if present). Note: when
            # emitting $SPLUNK_ETC exactly, with no additional path parts, we
            # set <relpath> to the empty string.
            relpath = relpath[4:]
        else:
            basepath = _splunk_home()

    fullpath = os.path.normpath(os.path.join(basepath, relpath))

    # Check that we haven't escaped from intended parent directories.
    if os.path.relpath(fullpath, basepath)[0:2] == '..':
        raise ValueError('Illegal escape from parent directory "%s": %s' %
                         (basepath, fullpath))
    return fullpath


def get_splunk_bin():
    '''Get absolute path of splunk CLI.

    :returns: absolute path of splunk CLI
    :rtype: ``string``
    '''

    if os.name == 'nt':
        splunk_bin = 'splunk.exe'
    else:
        splunk_bin = 'splunk'
    return make_splunkhome_path(('bin', splunk_bin))


def get_splunkd_serverinfo():
    '''Get splunkd server info.

    :returns: Splunkd server info (scheme, host, port)
    :rtype: ``tuple``
    '''

    server_conf = _get_conf_stanzas('server')
    if utils.is_true(server_conf['sslConfig']['enableSplunkdSSL']):
        scheme = 'https'
    else:
        scheme = 'http'

    web_conf = _get_conf_stanzas('web')
    host_port = web_conf['settings']['mgmtHostPort']
    host = host_port.split(':')[0]
    port = int(host_port.split(':')[1])

    if 'SPLUNK_BINDIP' in os.environ:
        bindip = os.environ['SPLUNK_BINDIP']
        port_idx = bindip.rfind(':')
        host = bindip[:port_idx] if port_idx > 0 else bindip

    return (scheme, host, port)


def get_splunkd_uri():
    '''Get splunkd uri.

    :returns: Splunkd uri
    :rtype: ``string``
    '''

    if os.environ.get('SPLUNKD_URI'):
        return os.environ['SPLUNKD_URI']

    scheme, host, port = get_splunkd_serverinfo()
    return '{scheme}://{host}:{port}'.format(scheme=scheme,
                                             host=host, port=port)


def _get_conf_stanzas(conf_name):
    '''Get stanzas of `conf_name`

    :param conf_name: Configure file name
    :returns: Config stanzas like: {stanza_name: stanza_configs}
    :rtype: ``dict``
    '''

    assert conf_name and isinstance(conf_name, basestring), \
        'conf_name is not a basestring: %s.' % conf_name

    if conf_name.endswith('.conf'):
        conf_name = conf_name[:-5]

    # TODO: dynamically caculate SPLUNK_HOME
    btool_cli = [op.join(os.environ['SPLUNK_HOME'], 'bin', 'btool'),
                 conf_name, 'list']

    p = subprocess.Popen(btool_cli,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, _ = p.communicate()

    out = StringIO(out)
    parser = ConfigParser()
    parser.optionxform = str
    parser.readfp(out)

    out = {}
    for section in parser.sections():
        out[section] = {item[0]: item[1] for item in parser.items(section)}
    return out
