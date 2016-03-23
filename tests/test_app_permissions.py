import sys
import os.path as op
import json
import pytest

from splunklib import binding
from splunklib import client

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import app_permissions
from splunksolutionlib import server_info


def test_app_permissions_request_queue(monkeypatch):
    test_app_permissions_request_queue._queue = []

    _mock_server_info_property = {'server_roles': ['cluster_search_head', 'search_head', 'kv_store', 'shc_captain'], 'version': '6.3.1511.2', 'serverName': 'testserver'}

    def _mock_kvstore_create(self, name, indexes = {}, fields = {}, **kwargs):
        pass

    def _mock_kvstore_list(self, count=None, **kwargs):
        return [client.KVStoreCollection(None, None)]

    def _mock_entity_init(self, service, path, **kwargs):
        pass

    def _mock_kvstore_data_init(self, collection):
        pass

    def _mock_kvstore_data_insert(self, data):
        record = json.loads(data)
        test_app_permissions_request_queue._queue.append(record)

    def _mock_kvstore_data_query(self, **query):
        return test_app_permissions_request_queue._queue

    monkeypatch.setattr(client.Service, 'info', _mock_server_info_property)
    monkeypatch.setattr(client.Entity, '__init__', _mock_entity_init)
    monkeypatch.setattr(client.KVStoreCollections, 'create', _mock_kvstore_create)
    monkeypatch.setattr(client.KVStoreCollections, 'list', _mock_kvstore_list)
    monkeypatch.setattr(client.KVStoreCollection, 'name', 'test_queue')
    monkeypatch.setattr(client.KVStoreCollectionData, '__init__', _mock_kvstore_data_init)
    monkeypatch.setattr(client.KVStoreCollection, 'data', client.KVStoreCollectionData(None))

    monkeypatch.setattr(client.KVStoreCollectionData, 'insert', _mock_kvstore_data_insert)
    monkeypatch.setattr(client.KVStoreCollectionData, 'query', _mock_kvstore_data_query)

    aprq = app_permissions.AppPermissionsRequestQueue('test_queue', common.SESSION_KEY, 'Splunk_TA_test')
    txn_id = aprq.create('data1')
    assert aprq.acknowledge(txn_id, 'data2') == txn_id
    assert aprq.get()['txn_id'] == txn_id
    assert len(aprq.poll(0)) == 2
