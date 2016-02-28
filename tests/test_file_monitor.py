import sys
import os
import os.path as op
import unittest as ut
import time

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.common import file_monitor as fm


class TestFileChangesChecker(ut.TestCase):

    def setUp(self):
        self._filename = op.sep.join([op.dirname(op.abspath(__file__)),
                                      "test.log"])
        with open(self._filename, "w") as fp:
            fp.write("abc")

        self._called = False

    def tearDown(self):
        os.remove(self._filename)

    def callback_when_file_changes(self, changed):
        self._called = True

    def test_check_changes(self):
        checker = fm.FileChangesChecker(self.callback_when_file_changes,
                                        [self._filename])
        res = checker.check_changes()
        self.assertFalse(res)
        self.assertFalse(self._called)

        time.sleep(1)
        with open(self._filename, "a") as fp:
            fp.write("efg")
        res = checker.check_changes()
        self.assertTrue(res)
        self.assertTrue(self._called)


class TestFileMonitor(ut.TestCase):

    def setUp(self):
        self._filename = op.sep.join([op.dirname(op.abspath(__file__)),
                                      "test.log"])
        with open(self._filename, "w") as fp:
            fp.write("abc")

        self._called = False

    def tearDown(self):
        os.remove(self._filename)

    def callback_when_file_changes(self, changed):
        self._called = True

    def test_check_monitor(self):
        monitor = fm.FileMonitor(self.callback_when_file_changes,
                                 [self._filename], interval=1)
        monitor.start()

        self.assertFalse(self._called)

        time.sleep(1)
        with open(self._filename, "w") as fp:
            fp.write("efg")
        time.sleep(2)
        self.assertTrue(self._called)

        monitor.stop()

if __name__ == "__main__":
    ut.main()
