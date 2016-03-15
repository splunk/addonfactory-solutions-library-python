import sys
import re
import json
import uuid
import os.path as op

from splunklib import binding

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import kvstore


def test_kvstore_manager(monkeypatch):
    test_kvstore_manager._kvstore = {}

    def _mock_kvstore_get(self, path_segment, owner=None, app=None, sharing=None,
                          **query):
        pattern1 = re.compile(r'.+/data/kvstoretest$')
        pattern2 = re.compile(r'.+/data/kvstoretest/([^$]+)$')

        if pattern1.match(path_segment):
            return common.make_response_record(
                json.dumps(test_kvstore_manager._kvstore.values()))

        if pattern2.match(path_segment):
            key = pattern2.match(path_segment).group(1)
            if key in test_kvstore_manager._kvstore:
                return common.make_response_record(
                    json.dumps(test_kvstore_manager._kvstore[key]))

        raise binding.HTTPError(
            common.make_response_record('HTTP 404 Not Found', status=404))

    def _mock_kvstore_post(self, path_segment, owner=None, app=None, sharing=None,
                           headers=None, **query):
        pattern1 = re.compile(r'.+/data/kvstoretest$')
        pattern2 = re.compile(r'.+/data/kvstoretest/batch_save$')
        pattern3 = re.compile(r'.+/data/kvstoretest/([^$]+)$')

        if pattern1.match(path_segment):
            record = json.loads(query['body'])
            key = uuid.uuid1().get_hex()
            record['_key'] = key
            test_kvstore_manager._kvstore[key] = record
            return common.make_response_record(json.dumps({'_key': key}))

        if pattern2.match(path_segment):
            records = json.loads(query['body'])
            keys = []
            for record in records:
                key = uuid.uuid1().get_hex()
                record['_key'] = key
                test_kvstore_manager._kvstore[key] = record
                keys.append(key)
            return common.make_response_record(json.dumps(keys))

        if pattern3.match(path_segment):
            key = pattern3.match(path_segment).group(1)
            if key in test_kvstore_manager._kvstore:
                record = json.loads(query['body'])
                record['_key'] = key
                test_kvstore_manager._kvstore[key] = record
                return common.make_response_record(json.dumps({'_key': key}))

        raise binding.HTTPError(
            common.make_response_record('HTTP 404 Not Found', status=404))

    def _mock_kvstore_delete(self, path_segment, owner=None, app=None, sharing=None,
                             **query):
        pattern1 = re.compile(r'.+/data/kvstoretest$')
        pattern2 = re.compile(r'.+/data/kvstoretest/([^$]+)$')

        if pattern1.match(path_segment):
            test_kvstore_manager._kvstore.clear()
            return common.make_response_record('')

        if pattern2.match(path_segment):
            key = pattern2.match(path_segment).group(1)
            if key in test_kvstore_manager._kvstore:
                del test_kvstore_manager._kvstore[key]
                return common.make_response_record('')

        raise binding.HTTPError(
            common.make_response_record('HTTP 404 Not Found', status=404))

    monkeypatch.setattr(binding.Context, 'get', _mock_kvstore_get)
    monkeypatch.setattr(binding.Context, 'post', _mock_kvstore_post)
    monkeypatch.setattr(binding.Context, 'delete', _mock_kvstore_delete)

    ksm = kvstore.KvStoreManager(common.SESSION_KEY, 'Splunk_TA_test')

    key1 = ksm.create('kvstoretest', {'name': 'test1'}, include_ts=True)
    key2, key3 = ksm.batch_create('kvstoretest',
                                  [{'name': 'test2'},
                                   {'name': 'test3'}], include_ts=True)

    record = ksm.get('kvstoretest', key1)
    del record['_time']
    assert record == {'name': 'test1', '_key': key1}

    records = sorted(ksm.query('kvstoretest'), key=lambda x: x['name'])
    for record in records:
        del record['_time']
    assert records == [{'name': 'test1', '_key': key1},
                       {'name': 'test2', '_key': key2},
                       {'name': 'test3', '_key': key3}]

    ksm.update('kvstoretest', key3, {'name': 'changed'}, include_ts=True)
    record = ksm.get('kvstoretest', key3)
    del record['_time']
    assert record == {'name': 'changed', '_key': key3}

    ksm.delete('kvstoretest', key1)
    assert len(ksm.query('kvstoretest')) == 2

    ksm.query_delete('kvstoretest')
    assert len(ksm.query('kvstoretest')) == 0
