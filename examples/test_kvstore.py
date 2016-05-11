import sys
import os.path as op
import json
import uuid
import pytest

from splunklib import client
from splunklib.binding import HTTPError

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib.credentials import get_session_key
import context


def test_kvstore():
    session_key = get_session_key(
        context.username, context.password, scheme=context.scheme,
        host=context.host, port=context.port)
    kvstore = client.Service(
        scheme=context.scheme, host=context.host, port=context.port,
        token=session_key, app=context.app, owner=context.owner,
        autologin=True).kvstore
    fields = {'id': 'string',
              'name': 'string',
              'user': 'string'}
    kvstore.create('sessions', fields=fields)

    collections = kvstore.list()
    collection_data = None
    for collection in collections:
        if collection.name == 'sessions':
            collection_data = collection.data
            break
    assert collection_data

    record = {'id': uuid.uuid4().hex,
              'name': 'session1',
              'user': 'admin'}
    _key = collection_data.insert(json.dumps(record))['_key']
    resp_record = collection_data.query_by_id(_key)
    resp_record = {key: resp_record[key]
                   for key in resp_record if not key.startswith('_')}
    assert sorted(resp_record.values()) == sorted(record.values())

    record = {'id': uuid.uuid4().hex,
              'name': 'session4',
              'user': 'test'}
    collection_data.update(_key, json.dumps(record))
    resp_record = collection_data.query_by_id(_key)
    resp_record = {key: resp_record[key]
                   for key in resp_record if not key.startswith('_')}
    assert sorted(resp_record.values()) == sorted(record.values())

    collection_data.delete_by_id(_key)
    with pytest.raises(HTTPError):
        collection_data.query_by_id(_key)
