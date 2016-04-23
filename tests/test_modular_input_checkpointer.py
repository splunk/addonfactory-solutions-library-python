import os
import sys
import shutil
import os.path as op

from splunklib import binding
from splunklib import client

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib.modular_input import KVStoreCheckpointer
from solnlib.modular_input import FileCheckpointer

cur_dir = op.dirname(op.abspath(__file__))


class TestKVStoreCheckpointer(object):
    KVSTORE_CHECKPOINTER_COLLECTION_NAME = 'TestKVStoreCheckpointer'

    _checkpoint_states = {}

    def _mock_kvstore_checkpointer_collections_get(
            self, name="", owner=None, app=None, sharing=None, **query):
        raise binding.HTTPError(common.make_response_record('', status=404))

    def _mock_kvstore_checkpointer_collections_create(
            self, name, indexes={}, fields={}, **kwargs):
        pass

    def _mock_kvstore_checkpointer_collections_list(self, count=None, **kwargs):
        return [client.KVStoreCollection(None, None)]

    def _mock_kvstore_checkpointer_collection_init(self, service, path, **kwargs):
        pass

    def _mock_kvstore_checkpointer_collection_data_init(self, collection):
        pass

    def _mock_kvstore_checkpointer_collection_data_batch_save(self, *documents):
        for document in documents:
            self._checkpoint_states[document['_key']] = document

    def _mock_kvstore_checkpointer_collection_data_query_by_id(self, id):
        try:
            return self._checkpoint_states[id]
        except:
            raise binding.HTTPError(common.make_response_record('', status=404))

    def _mock_kvstore_checkpointer_collection_data_delete_by_id(self, id):
        try:
            del self._checkpoint_states[id]
        except:
            raise binding.HTTPError(None, status=404)

    def test_kvstore_checkpoint_crud(self, monkeypatch):
        monkeypatch.setattr(
            client.KVStoreCollections, 'get',
            self._mock_kvstore_checkpointer_collections_get)
        monkeypatch.setattr(
            client.KVStoreCollections, 'create',
            self._mock_kvstore_checkpointer_collections_create)
        monkeypatch.setattr(
            client.KVStoreCollections, 'list',
            self._mock_kvstore_checkpointer_collections_list)
        monkeypatch.setattr(
            client.KVStoreCollection, '__init__',
            self._mock_kvstore_checkpointer_collection_init)
        monkeypatch.setattr(
            client.KVStoreCollection, 'name',
            self.KVSTORE_CHECKPOINTER_COLLECTION_NAME)
        monkeypatch.setattr(
            client.KVStoreCollectionData, '__init__',
            self._mock_kvstore_checkpointer_collection_data_init)
        monkeypatch.setattr(
            client.KVStoreCollectionData, 'batch_save',
            self._mock_kvstore_checkpointer_collection_data_batch_save)
        monkeypatch.setattr(
            client.KVStoreCollectionData, 'query_by_id',
            self._mock_kvstore_checkpointer_collection_data_query_by_id)
        monkeypatch.setattr(
            client.KVStoreCollectionData, 'delete_by_id',
            self._mock_kvstore_checkpointer_collection_data_delete_by_id)

        ck = KVStoreCheckpointer(
            TestKVStoreCheckpointer.KVSTORE_CHECKPOINTER_COLLECTION_NAME,
            common.SESSION_KEY,
            'Splunk_TA_test')

        ck.update('test_state_key1', 'test_state_value1')
        ck.batch_update([{'_key': 'test_state_key2',
                          'state': 'test_state_value2'},
                         {'_key': 'test_state_key3',
                          'state': 'test_state_value3'}])
        assert ck.get('test_state_key1') == 'test_state_value1'
        assert ck.get('test_state_key2') == 'test_state_value2'
        assert ck.get('test_state_key3') == 'test_state_value3'
        ck.delete('test_state_key1')
        ck.delete('test_state_key2')
        ck.delete('test_state_key3')
        assert ck.get('test_state_key1') is None
        assert ck.get('test_state_key2') is None
        assert ck.get('test_state_key3') is None


class TestFileCheckpointer(object):
    checkpoint_dir = op.join(cur_dir, '.checkpoint_dir')

    @classmethod
    def setup_class(cls):
        os.mkdir(cls.checkpoint_dir)

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.checkpoint_dir)

    def test_file_checkpoint_crud(self, monkeypatch):
        ck = FileCheckpointer(self.checkpoint_dir)

        ck.update('test_state_key1', 'test_state_value1')
        ck.batch_update([{'_key': 'test_state_key2',
                          'state': 'test_state_value2'},
                         {'_key': 'test_state_key3',
                          'state': 'test_state_value3'}])
        assert ck.get('test_state_key1') == 'test_state_value1'
        assert ck.get('test_state_key2') == 'test_state_value2'
        assert ck.get('test_state_key3') == 'test_state_value3'
        ck.delete('test_state_key1')
        ck.delete('test_state_key2')
        ck.delete('test_state_key3')
        assert ck.get('test_state_key1') is None
        assert ck.get('test_state_key2') is None
        assert ck.get('test_state_key3') is None
