import sys
import os
import os.path as op
import time

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.common import file_monitor


class TestFileChangesChecker(object):

    def setup(self):
        self._filename = '/tmp/test.log'
        with open(self._filename, 'w') as fp:
            fp.write('abc')

        self._called = False

    def teardown(self):
        os.remove(self._filename)

    def callback_when_file_changes(self, changed):
        self._called = True

    def test_check_changes(self):
        checker = file_monitor.FileChangesChecker(
            self.callback_when_file_changes,
            [self._filename])
        res = checker.check_changes()
        assert not res
        assert not self._called

        time.sleep(1)
        with open(self._filename, 'a') as fp:
            fp.write('efg')
        res = checker.check_changes()
        assert res
        assert self._called


class TestFileMonitor(object):

    def setup(self):
        self._filename = '/tmp/test.log'
        with open(self._filename, 'w') as fp:
            fp.write('abc')

        self._called = False

    def teardown(self):
        os.remove(self._filename)

    def callback_when_file_changes(self, changed):
        self._called = True

    def test_check_monitor(self):
        monitor = file_monitor.FileMonitor(
            self.callback_when_file_changes,
            [self._filename], interval=1)
        monitor.start()

        assert not self._called

        time.sleep(1)
        with open(self._filename, 'w') as fp:
            fp.write('efg')
        time.sleep(2)
        assert self._called

        monitor.stop()
