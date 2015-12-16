import os
import os.path as op
import subprocess
from ConfigParser import ConfigParser
from cStringIO import StringIO

import splunksolutionlib.common.utils as utils


def make_splunkhome_path(parts):
    """
    create a path string by the several parts of the path. For example,
    `parts` is ["etc", "apps", "Splunk_TA_aws"], the return path will be
    $SPLUNK_HOME/etc/apps/Splunk_TA_aws.
    Note this function assumed SPLUNK_HOME is in environment varialbes
    :parts: list or tuple which consists of the path part
    :return: full path if succeful, otherwise throw ValueError exception
    """

    relpath = os.path.normpath(os.path.join(*parts))

    basepath = os.environ["SPLUNK_HOME"]  # Assume SPLUNK_HOME env has been set

    fullpath = os.path.normpath(os.path.join(basepath, relpath))

    # Check that we haven't escaped from intended parent directories.
    if os.path.relpath(fullpath, basepath)[0:2] == "..":
        raise ValueError('Illegal escape from parent directory "%s": %s' %
                         (basepath, fullpath))

    return fullpath


def get_splunk_bin():
    """
    Return full path of splunk CLI
    """

    if os.name == "nt":
        splunk_bin = "splunk.exe"
    else:
        splunk_bin = "splunk"
    return make_splunkhome_path(("bin", splunk_bin))


def _get_merged_conf_raw(conf_name):
    """
    :conf_name: configure file name
    :return: raw output of all contents for the same conf file
    Note: it depends on SPLUNK_HOME env variable
    """

    assert conf_name

    if conf_name.endswith(".conf"):
        conf_name = conf_name[:-5]

    # FIXME dynamically caculate SPLUNK_HOME
    btool_cli = [op.join(os.environ["SPLUNK_HOME"], "bin", "btool"), conf_name,
                 "list"]

    try:
        p = subprocess.Popen(btool_cli,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
    except OSError:
        raise

    return out


def _get_conf_stanzas(conf_name):
    """
    :return: {stanza_name: stanza_configs}, dict of dict
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
    """
    :return: splunkd URI by parsing the web.conf and server.conf
    """

    if os.environ.get("SPLUNKD_URI"):
        return os.environ["SPLUNKD_URI"]

    server_conf = _get_conf_stanzas("server")
    if utils.is_true(server_conf["sslConfig"]["enableSplunkdSSL"]):
        http = "https://"
    else:
        http = "http://"

    web_conf = _get_conf_stanzas("web")
    host_port = web_conf["settings"]["mgmtHostPort"]
    splunkd_uri = "{http}{host_port}".format(http=http, host_port=host_port)

    if os.environ.get("SPLUNK_BINDIP"):
        bindip = os.environ["SPLUNK_BINDIP"]
        port_idx = bindip.rfind(":")
        if port_idx > 0:
            bindip = bindip[:port_idx]
        port = host_port[host_port.rfind(":"):]
        splunkd_uri = "{http}{bindip}{port}".format(
            http=http, bindip=bindip, port=port)
    return splunkd_uri
