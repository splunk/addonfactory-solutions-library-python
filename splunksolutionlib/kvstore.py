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
This module contains splunk kvstore related functionalities.
'''

import json
import time

from splunklib import binding

__all__ = ['KvStoreManager']


class KvStoreManager(object):
    '''This class is a wrapper of splunk kvstore.

    :param session_key: Splunk access token.
    :type session_key: ``string``
    :param app: App name of namespace.
    :type app: ``string``
    :param owner: (optional) Owner of namespace.
    :type owner: ``string``
    :param scheme: (optional) The scheme for accessing the service, default is `https`.
    :type scheme: ``string``
    :param host: (optional) The host name, default is `localhost`.
    :type host: ``string``
    :param port: (optional) The port number, default is 8089.
    :type port: ``integer``
    '''

    def __init__(self, session_key, app, owner='nobody',
                 scheme='https', host='localhost', port=8089):
        self._binding_context = binding.Context(scheme=scheme,
                                                host=host,
                                                port=port,
                                                token=session_key,
                                                app=app,
                                                owner=owner,
                                                autologin=True)

    def create(self, collection, record, include_ts=False):
        '''Create a record in `collection` of kvstore.

        :param collection: Collection name of kvstore.
        :type collection: ``string``
        :param record: Record to insert, like: {'id': 'xxxx', 'name': 'test'}.
        :type record: ``JSON Object``
        :param include_ts: (optional) Flag to indicate including timestamp,
            default is False.
        :type include_ts: ``bool``
        :returns: Record id.
        :rtype: ``string``

        Usage::

           >>> from splunksolutionlib import kvstore
           >>> kvm = kvstore.KvStoreManager(session_key, app_name)
           >>> kvm.create('collection_name', {'id': 'xxxx', 'name': 'test'},
                          include_ts=True)
           >>> returns: '56e7f661a61adc6de34aad52'
        '''

        path = 'storage/collections/data/{collection}'.format(
            collection=collection)

        if include_ts:
            record['_time'] = time.time()

        content = self._binding_context.post(
            path,
            headers=[('Content-Type', 'application/json')],
            body=json.dumps(record),
            output_mode='json').body.read()

        return json.loads(content)['_key']

    def batch_create(self, collection, records, include_ts=False):
        '''Create batch records in `collection` of kvstore.

        :param collection: Collection name of kvstore.
        :type collection: ``string``
        :param record: Records to insert, like: [{'id': 'xxxx', 'name': 'test1'},
                                                 {'id': 'yyyy', 'name': 'test2'}].
        :type record: ``list::JSON Object``
        :param include_ts: (optional) Flag to indicate including timestamp,
            default is False.
        :type include_ts: ``bool``
        :returns: Record id list.
        :rtype: ``list``

        Usage::

           >>> from splunksolutionlib import kvstore
           >>> kvm = kvstore.KvStoreManager(session_key, app_name)
           >>> kvm.batch_create('collection_name',
                                [{'id': 'xxxx', 'name': 'test1'},
                                 {'id': 'yyyy', 'name': 'test2'}],
                                include_ts=True)
           >>> returns: '(56e7f661a61adc6de34aad52, 56e7f661a61adc6de34aad53)'
        '''

        path = 'storage/collections/data/{collection}/batch_save'.format(
            collection=collection)

        if not isinstance(records, list):
            records = [records]

        if include_ts:
            curr = time.time()

            for record in records:
                record['_time'] = curr

        content = self._binding_context.post(
            path,
            headers=[('Content-Type', 'application/json')],
            body=json.dumps(records),
            output_mode='json').body.read()

        return json.loads(content)

    def query(self, collection, fields=None,
              limit=None, skip=None, sort=None, query=None):
        '''Query records based on `fields/limit/skip/sort/query`.

        :param collection: Collection name of kvstore.
        :type collection: ``string``
        :param fields: (optional) Comma-separated list of fields to include,
            like: fields='firstname,surname', default is None.
        :type fields: ``string``
        :param limit: (optional) Maximum number of items to return, default is
            None.
        :type limit: ``integer``
        :param skip: (optional) Number of items to skip from the start, default
            is None.
        :type skip: ``integer``
        :param sort: (optional) Sort order, like: sort='surname:-1,firstname:1'
            (Sort by surname, descending, after firstname), default is None.
        :type sort: ``string``
        :param query: (optional) Query JSON object, like: query={"price":{"$gt":5}}
            (Select all documents with price greater than 5), default is None.
        :type query: ``JSON Object``
        :returns: Record list.
        :rtype: ``list``

        Usage::

           >>> from splunksolutionlib import kvstore
           >>> kvm = kvstore.KvStoreManager(session_key, app_name)
           >>> kvm.query('kvstoretest', fields='name,_key',
                         limit=20, skip=2, sort='name,_key',
                         query={'_user': 'nobody'})
           >>> returns: '[{u'_key': u'56e8033aa61adc6de34aad5c', u'name': u'test3'},
                          {u'_key': u'56e8033aa61adc6de34aad5d', u'name': u'test4'}]'
        '''

        path = 'storage/collections/data/{collection}'.format(
            collection=collection)

        options = {}
        if fields:
            options['fields'] = fields
        if limit:
            options['limit'] = limit
        if skip:
            options['skip'] = skip
        if sort:
            options['sort'] = sort
        if query:
            options['query'] = json.dumps(query)
        options['output_mode'] = 'json'
        content = self._binding_context.get(
            path, **options).body.read()

        return json.loads(content)

    def query_delete(self, collection, query=None):
        '''Query records based on `query` and delete them.

        :param collection: Collection name of kvstore.
        :type collection: ``string``
        :param query: (optional) Query JSON object, like: query={"price":{"$gt":5}} (
            Select all documents with price greater than 5), default is None.
        :type query: ``JSON Object``

        Usage::

           >>> from splunksolutionlib import kvstore
           >>> kvm = kvstore.KvStoreManager(session_key, app_name)
           >>> kvm.query_delete('kvstoretest', query={'_user': 'nobody'})
        '''

        path = 'storage/collections/data/{collection}'.format(
            collection=collection)

        options = {}
        if query:
            options['query'] = json.dumps(query)

        self._binding_context.delete(
            path, **options)

    def update(self, collection, record_key, new_record, include_ts=False):
        '''Update record `record_key` with `new_record`.

        :param collection: Collection name of kvstore.
        :type collection: ``string``
        :param record_key: Record key.
        :type record_key: ``string``
        :param new_record: New record to update, like: {'id': 'xxxx', 'name': 'test'}.
        :type new_record: ``JSON Object``
        :param include_ts: (optional) Flag to indicate including timestamp, default
            is False.
        :returns: Record id.
        :rtype: ``string``

        Usage::

           >>> from splunksolutionlib import kvstore
           >>> kvm = kvstore.KvStoreManager(session_key, app_name)
           >>> kvm.update('collection_name', '56e8033aa61adc6de34aad5c',
                          {'id': 'xxxx', 'name': 'test'}, include_ts=True)
           >>> returns: '56e8033aa61adc6de34aad5c'
        '''

        path = 'storage/collections/data/{collection}/{record_key}'.format(
            collection=collection,
            record_key=record_key)

        if include_ts:
            new_record['_time'] = time.time()

        content = self._binding_context.post(
            path,
            headers=[('Content-Type', 'application/json')],
            body=json.dumps(new_record),
            output_mode='json').body.read()

        return json.loads(content)['_key']

    def get(self, collection, record_key):
        '''Get record `record_key`.

        :param collection: Collection name of kvstore.
        :type collection: ``string``
        :param record_key: Record key.
        :type record_key: ``string``
        :returns: Record.
        :rtype: ``JSON Object``

        Usage::

           >>> from splunksolutionlib import kvstore
           >>> kvm = kvstore.KvStoreManager(session_key, app_name)
           >>> kvm.get('collection_name', '56e8033aa61adc6de34aad5c')
           >>> returns: {'id': 'xxxx', 'name': 'test'}
        '''

        path = 'storage/collections/data/{collection}/{record_key}'.format(
            collection=collection,
            record_key=record_key)

        content = self._binding_context.get(
            path,
            output_mode='json').body.read()

        return json.loads(content)

    def delete(self, collection, record_key):
        '''Delete record `record_key`.

        :param collection: Collection name of kvstore.
        :type collection: ``string``
        :param record_key: Record key.
        :type record_key: ``string``

        Usage::

           >>> from splunksolutionlib import kvstore
           >>> kvm = kvstore.KvStoreManager(session_key, app_name)
           >>> kvm.delete('collection_name', '56e8033aa61adc6de34aad5c')
        '''

        path = 'storage/collections/data/{collection}/{record_key}'.format(
            collection=collection,
            record_key=record_key)

        self._binding_context.delete(path)
