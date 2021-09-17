#
# Copyright 2021 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""This module provides two kinds of checkpointer: KVStoreCheckpointer,
FileCheckpointer for modular input to save checkpoint."""

import base64
import json
import logging
import os
import os.path as op
import re
import traceback
from abc import ABCMeta, abstractmethod
from typing import List

from splunklib import binding

from .. import splunk_rest_client as rest_client
from ..utils import retry

__all__ = ["CheckpointerException", "KVStoreCheckpointer", "FileCheckpointer"]


class CheckpointerException(Exception):
    pass


class Checkpointer(metaclass=ABCMeta):
    """Base class of checkpointer."""

    @abstractmethod
    def update(self, key: str, state: dict):
        """Update checkpoint.

        Arguments:
            key: Checkpoint key.
            state: Checkpoint state.

        Examples:
           >>> from solnlib.modular_input import checkpointer
           >>> ck = checkpointer.KVStoreCheckpointer(session_key,
                                                     'Splunk_TA_test')
           >>> ck.update('checkpoint_name1', {'k1': 'v1', 'k2': 'v2'})
           >>> ck.update('checkpoint_name2', 'checkpoint_value2')
        """

        pass

    @abstractmethod
    def batch_update(self, states: List):
        """Batch update checkpoint.

        Arguments:
            states: List of checkpoint. Each state in the list is a
                json object which should contain '_key' and 'state' keys.
                For instance::

                    {
                        '_key': ckpt key which is a string,
                        'state': ckpt which is a json object
                    }

        Examples:
           >>> from solnlib.modular_input import checkpointer
           >>> ck = checkpointer.KVStoreCheckpointer(session_key,
                                                     'Splunk_TA_test')
           >>> ck.batch_update([{'_key': 'checkpoint_name1',
                                 'state': {'k1': 'v1', 'k2': 'v2'}},
                                {'_key': 'checkpoint_name2',
                                 'state': 'checkpoint_value2'},
                                {...}])
        """

        pass

    @abstractmethod
    def get(self, key: str) -> dict:
        """Get checkpoint.

        Arguments:
            key: Checkpoint key.

        Returns:
            Checkpoint state if exists else None.

        Examples:
           >>> from solnlib.modular_input import checkpointer
           >>> ck = checkpointer.KVStoreCheckpointer(session_key,
                                                     'Splunk_TA_test')
           >>> ck.get('checkpoint_name1')
           >>> returns: {'k1': 'v1', 'k2': 'v2'}
        """

        pass

    @abstractmethod
    def delete(self, key: str):
        """Delete checkpoint.

        Arguments:
            key: Checkpoint key.

        Examples:
           >>> from solnlib.modular_input import checkpointer
           >>> ck = checkpointer.KVStoreCheckpointer(session_key,
                                                     'Splunk_TA_test')
           >>> ck.delete('checkpoint_name1')
        """

        pass


class KVStoreCheckpointer(Checkpointer):
    """KVStore checkpointer.

    Use KVStore to save modular input checkpoint.

    Examples:
        >>> from solnlib.modular_input import checkpointer
        >>> ck = checkpoint.KVStoreCheckpointer('TestKVStoreCheckpointer',
                                                session_key,
                                                'Splunk_TA_test')
        >>> ck.update(...)
        >>> ck.get(...)
    """

    def __init__(
        self,
        collection_name: str,
        session_key: str,
        app: str,
        owner: str = "nobody",
        scheme: str = None,
        host: str = None,
        port: int = None,
        **context: dict
    ):
        """Initializes KVStoreCheckpointer.

        Arguments:
            collection_name: Collection name of kvstore checkpointer.
            session_key: Splunk access token.
            app: App name of namespace.
            owner: (optional) Owner of namespace, default is `nobody`.
            scheme: (optional) The access scheme, default is None.
            host: (optional) The host name, default is None.
            port: (optional) The port number, default is None.
            context: Other configurations for Splunk rest client.

        Raises:
            CheckpointerException: If init kvstore checkpointer failed.
        """
        try:
            self._collection_data = self._get_collection_data(
                collection_name, session_key, app, owner, scheme, host, port, **context
            )
        except KeyError:
            raise CheckpointerException("Get kvstore checkpointer failed.")

    @retry(exceptions=[binding.HTTPError])
    def _get_collection_data(
        self, collection_name, session_key, app, owner, scheme, host, port, **context
    ):

        if not context.get("pool_connections"):
            context["pool_connections"] = 5

        if not context.get("pool_maxsize"):
            context["pool_maxsize"] = 5

        kvstore = rest_client.SplunkRestClient(
            session_key,
            app,
            owner=owner,
            scheme=scheme,
            host=host,
            port=port,
            **context
        ).kvstore

        collection_name = re.sub(r"[^\w]+", "_", collection_name)
        try:
            kvstore.get(name=collection_name)
        except binding.HTTPError as e:
            if e.status != 404:
                raise

            fields = {"state": "string"}
            kvstore.create(collection_name, fields=fields)

        collections = kvstore.list(search=collection_name)
        for collection in collections:
            if collection.name == collection_name:
                return collection.data
        else:
            raise KeyError("Get collection data: %s failed." % collection_name)

    @retry(exceptions=[binding.HTTPError])
    def update(self, key, state):
        record = {"_key": key, "state": json.dumps(state)}
        self._collection_data.batch_save(record)

    @retry(exceptions=[binding.HTTPError])
    def batch_update(self, states):
        for state in states:
            state["state"] = json.dumps(state["state"])
        self._collection_data.batch_save(*states)

    @retry(exceptions=[binding.HTTPError])
    def get(self, key):
        try:
            record = self._collection_data.query_by_id(key)
        except binding.HTTPError as e:
            if e.status != 404:
                logging.error("Get checkpoint failed: %s.", traceback.format_exc())
                raise

            return None

        return json.loads(record["state"])

    @retry(exceptions=[binding.HTTPError])
    def delete(self, key):
        try:
            self._collection_data.delete_by_id(key)
        except binding.HTTPError as e:
            if e.status != 404:
                logging.error("Delete checkpoint failed: %s.", traceback.format_exc())
                raise


class FileCheckpointer(Checkpointer):
    """File checkpointer.

    Use file to save modular input checkpoint.

    Examples:
        >>> from solnlib.modular_input import checkpointer
        >>> ck = checkpointer.FileCheckpointer('/opt/splunk/var/...')
        >>> ck.update(...)
        >>> ck.get(...)
    """

    def __init__(self, checkpoint_dir: str):
        """Initializes FileCheckpointer.

        Arguments:
            checkpoint_dir: Checkpoint directory.
        """
        self._checkpoint_dir = checkpoint_dir

    def encode_key(self, key):
        return base64.b64encode(key.encode()).decode()

    def update(self, key, state):
        file_name = op.join(self._checkpoint_dir, self.encode_key(key))
        with open(file_name + "_new", "w") as fp:
            json.dump(state, fp)

        if op.exists(file_name):
            try:
                os.remove(file_name)
            except OSError:
                pass

        os.rename(file_name + "_new", file_name)

    def batch_update(self, states):
        for state in states:
            self.update(state["_key"], state["state"])

    def get(self, key):
        file_name = op.join(self._checkpoint_dir, self.encode_key(key))
        try:
            with open(file_name) as fp:
                return json.load(fp)
        except (OSError, ValueError):
            return None

    def delete(self, key):
        file_name = op.join(self._checkpoint_dir, self.encode_key(key))
        try:
            os.remove(file_name)
        except OSError:
            pass
