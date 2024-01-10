#
# Copyright 2024 Splunk Inc.
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

import os
import tempfile
import time
from unittest import mock

from solnlib import file_monitor


class TestFileChangesChecker:
    def test_check_changes(self):
        with tempfile.NamedTemporaryFile() as tmpfile:
            self._called = False

            def _callback_when_file_changes(changed):
                self._called = True

            checker = file_monitor.FileChangesChecker(
                _callback_when_file_changes, [tmpfile.name]
            )
            res = checker.check_changes()
            assert res is False
            assert self._called is False

            time.sleep(1)
            with open(tmpfile.name, "a") as fp:
                fp.write("some changes")
            res = checker.check_changes()
            assert res is True
            assert self._called is True

    @mock.patch("os.path.getmtime")
    def test_check_changes_when_os_errors(self, mock_os_path_getmtime):
        with tempfile.TemporaryDirectory() as tmpdirname:
            file_1 = os.path.join(tmpdirname, "file_1")
            file_2 = os.path.join(tmpdirname, "file_2")
            with open(file_1, "w") as f1:
                f1.write("content 1")
            with open(file_2, "w") as f2:
                f2.write("content 2")

            mock_os_path_getmtime.side_effect = [
                OSError,
                OSError,
            ]
            checker = file_monitor.FileChangesChecker(
                lambda _: _,
                [
                    file_1,
                    file_2,
                ],
            )
            assert {file_1: None, file_2: None} == checker.file_mtimes

    @mock.patch("os.path.getmtime")
    def test_check_changes_when_os_errors_for_one_file(self, mock_os_path_getmtime):
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._changed = None

            def _callback_when_file_changes(changed):
                self._changed = changed

            file_1 = os.path.join(tmpdirname, "file_1")
            file_2 = os.path.join(tmpdirname, "file_2")
            with open(file_1, "w") as f1:
                f1.write("content 1")
            with open(file_2, "w") as f2:
                f2.write("content 2")

            def _side_effect(file):
                if file == file_1:
                    return time.time()
                else:
                    raise OSError

            mock_os_path_getmtime.side_effect = _side_effect
            checker = file_monitor.FileChangesChecker(
                _callback_when_file_changes,
                [
                    file_1,
                    file_2,
                ],
            )
            with open(file_1, "a") as f1:
                f1.write("append 1")
            assert checker.check_changes()
            assert [file_1] == self._changed


class TestFileMonitor:
    def test_check_monitor(self):
        with tempfile.NamedTemporaryFile() as tmpfile:
            self._called = False

            def _callback_when_file_changes(changed):
                self._called = True

            monitor = file_monitor.FileMonitor(
                _callback_when_file_changes, [tmpfile.name], interval=1
            )
            monitor.start()
            assert self._called is False

            time.sleep(1)
            with open(tmpfile.name, "w") as fp:
                fp.write("some changes")
            time.sleep(2)
            assert self._called is True

            monitor.stop()

    @mock.patch("threading.Thread")
    def test_two_times_start_calls_check_changes_only_once(self, mock_thread_class):
        mock_thread = mock.MagicMock()
        mock_thread_class.return_value = mock_thread
        with tempfile.NamedTemporaryFile() as tmpfile:
            monitor = file_monitor.FileMonitor(lambda _: _, [tmpfile.name])
            monitor.start()
            time.sleep(1)
            monitor.start()
            mock_thread.start.assert_called_once()
            monitor.stop()
