# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

import sys
import time
import os
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
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
