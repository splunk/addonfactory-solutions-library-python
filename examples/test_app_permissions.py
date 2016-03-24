import sys
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.app_permissions import AppPermissionsRequestQueue
from splunksolutionlib.credentials import get_session_key
import context


def test_app_permissions_request_queue():
    session_key = get_session_key(
        context.username, context.password, scheme=context.scheme,
        host=context.host, port=context.port)

    aprq = AppPermissionsRequestQueue('splunksolutionlib_activity_queue',
                                      session_key, context.app, owner=context.owner,
                                      scheme=context.scheme, host=context.host,
                                      port=context.port)
    txn_id1 = aprq.create('splunksolutionlib_activity_data1')
    aprq.create('splunksolutionlib_activity_data2')
    aprq.create('splunksolutionlib_activity_data3')
    assert aprq.get() is None

    aprq.acknowledge(txn_id1, 'splunksolutionlib_activity_complete_data1')
    assert aprq.get()['data'] == 'splunksolutionlib_activity_complete_data1'

    records = aprq.poll(0)
    assert len(records) == 4
    assert sorted(
        ['splunksolutionlib_activity_data1',
         'splunksolutionlib_activity_data2',
         'splunksolutionlib_activity_data3',
         'splunksolutionlib_activity_complete_data1']) == sorted([record['data'] for record in records])
