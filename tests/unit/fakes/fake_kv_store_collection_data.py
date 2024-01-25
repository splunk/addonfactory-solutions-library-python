#
# Copyright 2023 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json

import common
from splunklib import client


class FakeKVStoreCollectionDataThrowingExceptions:
    """Fake implementation of KVStoreCollectionData for
    splunklib.client.KVStoreCollectionData which always throws
    splunklib.client.HTTPError."""

    def query_by_id(self, key):
        raise client.HTTPError(
            common.make_response_record(
                b"",
                status=503,
            )
        )

    def delete_by_id(self, key):
        raise client.HTTPError(
            common.make_response_record(
                b"",
                status=503,
            )
        )


class FakeKVStoreCollectionData:
    """Fake implementation of KVStoreCollectionData for
    splunklib.client.KVStoreCollectionData."""

    def __init__(self, documents=None):
        self._documents = {}
        if documents is not None:
            for document in documents:
                self._documents[document["_key"]] = {
                    "_key": document["_key"],
                    "state": json.dumps(document["state"]),
                }

    def get(self, _id):
        return self._documents.get(_id)

    def id_exists(self, _id):
        return True if _id in self._documents else False

    def batch_save(self, *documents):
        for document in documents:
            self._documents[document["_key"]] = document

    def delete_by_id(self, _id):
        if _id in self._documents:
            del self._documents[_id]
        else:
            raise client.HTTPError(
                common.make_response_record(
                    b"",
                    status=404,
                )
            )

    def query_by_id(self, _id):
        if _id in self._documents:
            return self._documents[_id]
        else:
            raise client.HTTPError(
                common.make_response_record(
                    b"",
                    status=404,
                )
            )
