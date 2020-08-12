import os.path as op
import sys

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import server_info
from solnlib.credentials import get_session_key
import context


def test_server_info():
    session_key = get_session_key(
        context.username, context.password, scheme=context.scheme,
        host=context.host, port=context.port)

    si = server_info.ServerInfo(session_key, scheme=context.scheme,
                                host=context.host, port=context.port)
    print 'Local splunk server info'

    print '    -name: ', si.server_name

    print '    -version: ', si.version

    print '    -is a cluster captain: ', si.is_captain()

    print '    -is a clound instance: ', si.is_cloud_instance()

    print '    -is a search head: ', si.is_search_head()

    print '    -is a SHC member: ', si.is_shc_member()

    try:
        shc_members = si.get_shc_members()
    except server_info.ServerInfoException as e:
        print e.message
    else:
        print '    -SHC members are: ', shc_members
