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
    __metaclass__ = ABCMeta

    @abstractmethod
    def update(self, key, state):
        pass

    @abstractmethod
    def batch_update(self, states):
        pass

    @abstractmethod
    def get(self, key):
        pass

    @abstractmethod
    def delete(self, key):
        pass


class KVStoreCheckpoint(Checkpoint):
    CHECKPOINT_COLLECTION = 'modularinput_checkpoint'

    def __init__(self, session_key, app, owner='nobody',
                 scheme='https', host='localhost', port=8089):
        kvstore = Service(scheme=scheme,
                          host=host,
                          port=port,
                          token=session_key,
                          app=app,
                          owner=owner,
                          autologin=True).kvstore
        try:
            kvstore.get(name=self.CHECKPOINT_COLLECTION)
        except HTTPError:
            fields = {'state': 'string'}
            kvstore.create(self.CHECKPOINT_COLLECTION, fields=fields)

        self._collection_data = None
        collections = kvstore.list()
        for collection in collections:
            if collection.name == self.CHECKPOINT_COLLECTION:
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
