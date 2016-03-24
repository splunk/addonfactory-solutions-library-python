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
This module contains interfaces of app permissions management.
'''

import time
import uuid
import json

from splunklib import binding
from splunklib import client
from splunksolutionlib import server_info


class AppPermissionsRequestQueueError(Exception):
    pass


class AppPermissionsRequestQueue(object):
    '''App permissions request queue.

    This class provides interfaces of app permissions management.

    :param queue: App permissions request queue name.
    :type queue: ``string``
    :param session_key: Splunk access token.
    :type session_key: ``string``
    :param app: App name of namespace.
    :type app: ``string``
    :param owner: (optional) Owner of namespace.
    :type owner: ``string``
    :param scheme: (optional) The access scheme, default is `https`.
    :type scheme: ``string``
    :param host: (optional) The host name, default is `localhost`.
    :type host: ``string``
    :param port: (optional) The port number, default is 8089.
    :type port: ``integer``

    :Raises AppPermissionsRequestQueueError: If get app permissions queue
        failed.

    Usage::

       >>> import splunksolutionlib.app_permissions as sap
       >>> saprq = sap.AppPermissionsRequestQueue(
                       'test_activity_queue', session_key, 'Splunk_TA_test')
       >>> saprq.create(data)
       >>> saprq.acknowledge(txn_id, data)
       >>> saprq.get()
       >>> returns: {record1}
       >>> saprq.poll(timestamp)
       >>> [{record1}, {record2}, {record3}, ...]
    '''

    REQUEST_NEW = 'request'
    REQUEST_COMPLETE = 'complete'
    CATEGORY = 'app_permissions'

    def __init__(self, queue, session_key, app, owner='nobody',
                 scheme='https', host='localhost', port=8089):
        self._server_name = server_info.ServerInfo(
            session_key, scheme=scheme, host=host, port=port).server_name

        kvstore = client.Service(
            scheme=scheme, host=host, port=port, token=session_key,
            app=app, owner=owner, autologin=True).kvstore
        try:
            kvstore.get(name=queue)
        except binding.HTTPError:
            fields = {'action': 'string',
                      'category': 'string',
                      'txn_id': 'string',
                      'data': 'string',
                      'splunk_server': 'string',
                      'time': 'time',
                      'user': 'string'}
            kvstore.create(queue, fields=fields)

        collections = kvstore.list()
        self._collection_data = None
        for collection in collections:
            if collection.name == queue:
                self._collection_data = collection.data
                break

        if self._collection_data is None:
            raise AppPermissionsRequestQueueError(
                'Get app permissions request queue: %s failed.', queue)

    def get(self):
        query = {'category': self.CATEGORY,
                 'action': self.REQUEST_COMPLETE}

        records = self._collection_data.query(limit=1, query=json.dumps(query),
                                              sort='time:-1')
        if records:
            return records[0]
        else:
            return None

    def create(self, data):
        txn_id = uuid.uuid4().hex
        self._create(self.REQUEST_NEW, txn_id, data)

        return txn_id

    def acknowledge(self, txn_id, data):
        self._create(self.REQUEST_COMPLETE, txn_id, data)

        return txn_id

    def _create(self, action, txn_id, data, user=None):
        record = {'action': action,
                  'category': self.CATEGORY,
                  'txn_id': txn_id,
                  'data': data,
                  'splunk_server': self._server_name,
                  'time': time.time(),
                  'user': user}

        self._collection_data.insert(json.dumps(record))

    def poll(self, timestamp):
        query = {'category': self.CATEGORY,
                 'time': {'$gte': timestamp}}

        return self._collection_data.query(query=json.dumps(query),
                                           sort='time:1')
