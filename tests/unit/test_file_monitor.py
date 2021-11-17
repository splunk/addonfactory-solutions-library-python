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
import time

from solnlib import file_monitor

_monitor_file = "./.test_monitor_file"


def setup_module(module):
    with open(_monitor_file, "w") as fp:
        fp.write("abc")


def teardown_module(module):
    os.remove(_monitor_file)


class TestFileChangesChecker:
    def test_check_changes(self, monkeypatch):
        self._called = False

        def _callback_when_file_changes(changed):
            self._called = True

        checker = file_monitor.FileChangesChecker(
            _callback_when_file_changes, [_monitor_file]
        )
        res = checker.check_changes()
        assert res is False
        assert self._called is False

        time.sleep(1)
        with open(_monitor_file, "a") as fp:
            fp.write("efg")
        res = checker.check_changes()
        assert res is True
        assert self._called is True


class TestFileMonitor:
    def test_check_monitor(self, monkeypatch):
        self._called = False

        def _callback_when_file_changes(changed):
            self._called = True

        monitor = file_monitor.FileMonitor(
            _callback_when_file_changes, [_monitor_file], interval=1
        )
        monitor.start()
        assert self._called is False

        time.sleep(1)
        with open(_monitor_file, "w") as fp:
            fp.write("efg")
        time.sleep(2)
        assert self._called is True

        monitor.stop()
