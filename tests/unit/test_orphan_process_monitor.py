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

import os
import random
import time

from solnlib import orphan_process_monitor as opm


def _mock_getppid():
    return random.randint(1, 65535)


class TestOrphanProcessChecker:
    def setup(self):
        self._called = False

    def test_is_orphan(self, monkeypatch):
        monkeypatch.setattr(os, "getppid", _mock_getppid)

        def orphan_callback():
            self._called = True

        checker = opm.OrphanProcessChecker(callback=orphan_callback)
        res = checker.is_orphan()
        assert res
        res = checker.check_orphan()
        assert res
        assert self._called


class TestOrphanProcessMonitor:
    def setup(self):
        self._called = False

    def test_monitor(self, monkeypatch):
        monkeypatch.setattr(os, "getppid", _mock_getppid)

        def orphan_callback():
            self._called = True

        monitor = opm.OrphanProcessMonitor(callback=orphan_callback)
        monitor.start()

        time.sleep(1)
        assert self._called

        monitor.stop()
