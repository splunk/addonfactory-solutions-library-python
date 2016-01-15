import os
import os.path as op
import unittest as ut
import time

from splunksolutionlib.common import file_monitor as fm


class TestFileChangesChecker(ut.TestCase):

    def setUp(self):
        curdir = op.dirname(op.abspath(__file__))
        self._filename = op.join(curdir, "test.log")
        with open(self._filename, "w") as f:
            f.write("abc")

        self._checker = fm.FileChangesChecker(self.callback_when_file_changes,
                                              [self._filename])
        self._called = False
        # Sleep 1 second to avoid the test case to run too fast
        # the granularity of the last modified may be second, if the test case
        # finishes within 1 second, we can't detect the changes
        time.sleep(1)

    def tearDown(self):
        os.remove(self._filename)

    def callback_when_file_changes(self, changed):
        self._called = True

    def test_check_changes(self):
        res = self._checker.check_changes()
        self.assertFalse(res)
        self.assertFalse(self._called)

        with open(self._filename, "a") as f:
            f.write("efg")

        res = self._checker.check_changes()
        self.assertTrue(res)
        self.assertTrue(self._called)


class TestFileMonitor(ut.TestCase):

    def setUp(self):
        curdir = op.dirname(op.abspath(__file__))
        self._filename = op.join(curdir, "test.log")
        with open(self._filename, "w") as f:
            f.write("abc")

        self._monitor = fm.FileMonitor(self.callback_when_file_changes,
                                       [self._filename], interval=1)
        self._monitor.start()
        self._called = False
        time.sleep(1)

    def tearDown(self):
        self._monitor.stop()
        os.remove(self._filename)

    def callback_when_file_changes(self, changed):
        self._called = True

    def test_check_monitor(self):
        time.sleep(2)
        self.assertFalse(self._called)

        with open(self._filename, "w") as f:
            f.write("efg")

        time.sleep(1)
        self.assertTrue(self._called)


if __name__ == "__main__":
    ut.main()
