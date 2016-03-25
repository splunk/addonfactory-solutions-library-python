import sys
import os.path as op
import json
import StringIO

from splunklib import client

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.app_permissions import AppPermissionsRequestQueue


class TestAppPermissionsRequestQueue(object):
    _queue = []

    def _mock_kvstore_entity_init(self, service, path, **kwargs):
        pass

    def _mock_kvstore_create(self, name, indexes={}, fields={}, **kwargs):
        pass

    def _mock_kvstore_get(self, name="", owner=None, app=None, sharing=None, **query):
        class HttpResponse(object):
            status = 404
            reason = 'Not found'
            headers = []
            body = StringIO.StringIO('Not found')

        raise client.HTTPError(HttpResponse())

    def _mock_kvstore_list(self, count=None, **kwargs):
        return [client.KVStoreCollection(None, None)]

    def _mock_kvstore_data_init(self, collection):
        pass

    def _mock_kvstore_data_insert(self, data):
        record = json.loads(data)
        TestAppPermissionsRequestQueue._queue.append(record)

    def _mock_kvstore_data_query(self, **query):
        if 'limit' in query:
            records = []
            for record in reversed(TestAppPermissionsRequestQueue._queue):
                if record['action'] == AppPermissionsRequestQueue.REQUEST_COMPLETE:
                    records.append(record)
            return records
        else:
            return TestAppPermissionsRequestQueue._queue

    def test_create(self, monkeypatch):
        common.mock_serverinfo(monkeypatch)
        monkeypatch.setattr(client.Entity, '__init__', self._mock_kvstore_entity_init)
        monkeypatch.setattr(client.KVStoreCollection, 'name', 'unittest_queue')
        monkeypatch.setattr(client.KVStoreCollections, 'create', self._mock_kvstore_create)
        monkeypatch.setattr(client.KVStoreCollections, 'get', self._mock_kvstore_get)
        monkeypatch.setattr(client.KVStoreCollections, 'list', self._mock_kvstore_list)
        monkeypatch.setattr(client.KVStoreCollectionData, '__init__', self._mock_kvstore_data_init)
        monkeypatch.setattr(client.KVStoreCollectionData, 'insert', self._mock_kvstore_data_insert)
        monkeypatch.setattr(client.KVStoreCollectionData, 'query', self._mock_kvstore_data_query)
        monkeypatch.setattr(client.KVStoreCollection, 'data', client.KVStoreCollectionData(None))

        aprq = AppPermissionsRequestQueue('unittest_queue', common.SESSION_KEY, common.app)
        TestAppPermissionsRequestQueue.txn_id = aprq.create('data1')
        assert aprq.get() is None
        assert aprq.poll(0)[0]['data'] == 'data1'

    def test_acknowledge(self, monkeypatch):
        common.mock_serverinfo(monkeypatch)
        monkeypatch.setattr(client.Entity, '__init__', self._mock_kvstore_entity_init)
        monkeypatch.setattr(client.KVStoreCollection, 'name', 'unittest_queue')
        monkeypatch.setattr(client.KVStoreCollections, 'create', self._mock_kvstore_create)
        monkeypatch.setattr(client.KVStoreCollections, 'get', self._mock_kvstore_get)
        monkeypatch.setattr(client.KVStoreCollections, 'list', self._mock_kvstore_list)
        monkeypatch.setattr(client.KVStoreCollectionData, '__init__', self._mock_kvstore_data_init)
        monkeypatch.setattr(client.KVStoreCollectionData, 'insert', self._mock_kvstore_data_insert)
        monkeypatch.setattr(client.KVStoreCollectionData, 'query', self._mock_kvstore_data_query)
        monkeypatch.setattr(client.KVStoreCollection, 'data', client.KVStoreCollectionData(None))

        aprq = AppPermissionsRequestQueue('unittest_queue', common.SESSION_KEY, common.app)
        aprq.acknowledge(TestAppPermissionsRequestQueue.txn_id, 'data2')
        assert aprq.get()['data'] == 'data2'
        assert len(aprq.poll(0)) == 2
