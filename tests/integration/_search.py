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
import context
import os.path as op
import sys
import time

from splunklib import client
from splunklib import results as splunklib_results

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))


def search(session_key, query):
    service = client.connect(host=context.host, token=session_key)
    job = service.jobs.create(query)
    while True:
        while not job.is_ready():
            pass
        stats = {
            "isDone": job["isDone"],
            "doneProgress": job["doneProgress"],
            "scanCount": job["scanCount"],
            "eventCount": job["eventCount"],
            "resultCount": job["resultCount"],
        }
        if stats["isDone"] == "1":
            break
        time.sleep(0.5)
    json_results_reader = splunklib_results.JSONResultsReader(
        job.results(output_mode="json")
    )
    results = []
    for result in json_results_reader:
        if isinstance(result, dict):
            results.append(result)
    return results
