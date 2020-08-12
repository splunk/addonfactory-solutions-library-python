from builtins import range
import json
import os.path as op
import sys
import time
import uuid

import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib.credentials import get_session_key
import context
from solnlib.packages.splunklib import binding
from solnlib.packages.splunklib import client
from solnlib.packages.splunklib.binding import HTTPError


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

    last_ex = None
    for i in range(3):
        try:
            kvstore.create('sessions', fields=fields)
            break
        except binding.HTTPError as e:
            last_ex = e
            time.sleep(2 ** (i + 1))
    else:
        if last_ex:
            raise last_ex

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
