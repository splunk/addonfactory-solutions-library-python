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
This module provides two kinds of checkpoint (KVStoreCheckpoint, FileCheckpoint)
for modular input.
'''

import os
import json
import base64
import os.path as op
from abc import ABCMeta, abstractmethod

from splunklib.binding import HTTPError
from splunklib.client import Service


class CheckpointException(Exception):
    pass


class Checkpoint(object):
    '''Base class of checkpoint.
    '''

    __metaclass__ = ABCMeta

    @abstractmethod
    def update(self, key, state):
        '''Update checkpoint.

        :param key: Checkpoint key.
        :type key: ``string``
        :param state: Checkpoint sate.
        :type state: ``json object``

        Usage::
           >>> from splunksolutionlib.modular_input import checkpoint
           >>> ck = checkpoint.KVStoreCheckpoint(session_key,
                                                'Splunk_TA_test')
           >>> ck.update('checkpoint_name1', {'k1': 'v1', 'k2': 'v2'})
           >>> ck.update('checkpoint_name2', 'checkpoint_value2')
        '''

        pass

    @abstractmethod
    def batch_update(self, states):
        '''Batch update checkpoint.

        :param records: List of checkpoint.
        :type state: ``list``

        Usage::
           >>> from splunksolutionlib.modular_input import checkpoint
           >>> ck = checkpoint.KVStoreCheckpoint(session_key,
                                                'Splunk_TA_test')
           >>> ck.batch_update([{'_key': 'checkpoint_name1',
                                 'state': {'k1': 'v1', 'k2': 'v2'}},
                                {'_key': 'checkpoint_name2',
                                 'state': 'checkpoint_value2'},
                                {...}])
        '''

        pass

    @abstractmethod
    def get(self, key):
        '''Get checkpoint.

        :param key: Checkpoint key.
        :type key: ``string``
        :returns: Checkpoint state if exists else None.
        :rtype: ``json object``

        Usage::
           >>> from splunksolutionlib.modular_input import checkpoint
           >>> ck = checkpoint.KVStoreCheckpoint(session_key,
                                                'Splunk_TA_test')
           >>> ck.get('checkpoint_name1')
           >>> returns: {'k1': 'v1', 'k2': 'v2'}
        '''

        pass

    @abstractmethod
    def delete(self, key):
        '''Delete checkpoint.

        :param key: Checkpoint key.
        :type key: ``string``

        Usage::
           >>> from splunksolutionlib.modular_input import checkpoint
           >>> ck = checkpoint.KVStoreCheckpoint(session_key,
                                                'Splunk_TA_test')
           >>> ck.delete('checkpoint_name1')
        '''

        pass


class KVStoreCheckpoint(Checkpoint):
    '''KVStore checkpoint.

    Use KVStore to save modular input checkpoint.

    :param collection_name: Collection name of kvstore checkpoint.
    :type collection_name: ``string``
    :param session_key: Splunk access token.
    :type session_key: ``string``
    :param app: App name of namespace.
    :type app: ``string``
    :param owner: (optional) Owner of namespace, default is `nobody`.
    :type owner: ``string``
    :param scheme: (optional) The access scheme, default is `https`.
    :type scheme: ``string``
    :param host: (optional) The host name, default is `localhost`.
    :type host: ``string``
    :param port: (optional) The port number, default is 8089.
    :type port: ``integer``

    Usage::
        >>> from splunksolutionlib.modular_input import checkpoint
        >>> ck = checkpoint.KVStoreCheckpoint(session_key,
                                            'Splunk_TA_test')
        >>> ck.update(...)
        >>> ck.get(...)
    '''

    def __init__(self, collection_name, session_key, app, owner='nobody',
                 scheme='https', host='localhost', port=8089):
        kvstore = Service(scheme=scheme,
                          host=host,
                          port=port,
                          token=session_key,
                          app=app,
                          owner=owner,
                          autologin=True).kvstore
        try:
            kvstore.get(name=collection_name)
        except HTTPError:
            fields = {'state': 'string'}
            kvstore.create(collection_name, fields=fields)

        self._collection_data = None
        collections = kvstore.list()
        for collection in collections:
            if collection.name == collection_name:
                self._collection_data = collection.data
                break

        if self._collection_data is None:
            raise CheckpointException(
                'Get modular input kvstore checkpoint failed.')

    def update(self, key, state):
        record = {'_key': key, 'state': json.dumps(state)}
        self._collection_data.batch_save(record)

    def batch_update(self, records):
        for record in records:
            record['state'] = json.dumps(record['state'])
            self._collection_data.batch_save(*records)

    def get(self, key):
        try:
            record = self._collection_data.query_by_id(key)
        except HTTPError:
            return None

        return json.loads(record['state'])

    def delete(self, key):
        try:
            self._collection_data.delete_by_id(key)
        except HTTPError:
            pass


class FileCheckpoint(Checkpoint):
    '''File checkpoint.

    Use file to save modular input checkpoint.

    :param checkpoint_dir: Checkpoint directory.
    :type checkpoint_dir: ``string``

    Usage::
        >>> from splunksolutionlib.modular_input import checkpoint
        >>> ck = checkpoint.FileCheckpoint('/opt/splunk/var/...')
        >>> ck.updtae(...)
        >>> ck.get(...)
    '''

    def __init__(self, checkpoint_dir):
        self._checkpoint_dir = checkpoint_dir

    def update(self, key, state):
        file_name = op.join(self._checkpoint_dir, base64.b64encode(key))
        with open(file_name + '_new', 'w') as fp:
            json.dump(state, fp)

        if os.exists(file_name):
            try:
                os.remove(file_name)
            except IOError:
                pass

        os.rename(file_name + '_new', file_name)

    def batch_update(self, records):
        for record in records:
            self.update(record['_key'], record['state'])

    def get(self, key):
        file_name = op.join(self._checkpoint_dir, base64.b64encode(key))
        try:
            with open(file_name, 'r') as fp:
                return json.load(fp)
        except (IOError, ValueError):
            return None

    def delete(self, key):
        file_name = op.join(self._checkpoint_dir, base64.b64encode(key))
        try:
            os.remove(file_name)
        except (OSError):
            pass
