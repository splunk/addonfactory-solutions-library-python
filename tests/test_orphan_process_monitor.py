import sys
import os
import os.path as op
import unittest as ut
import time
import random

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.common import orphan_process_monitor as opm


def mock_getppid():
    return random.randint(1, 65535)


class TestOrphanProcessChecker(ut.TestCase):

    def setUp(self):
        self._called = False
        self._old_getppid = os.getppid
        os.getppid = mock_getppid

    def tearDown(self):
        os.getppid = self._old_getppid

    def orphan_callback(self):
        self._called = True

    def test_is_orphan(self):
        checker = opm.OrphanProcessChecker(callback=self.orphan_callback)
        res = checker.is_orphan()
        self.assertTrue(res)
        res = checker.check_orphan()
        self.assertTrue(res)
        self.assertTrue(self._called)


class TestOrphanProcessMonitor(ut.TestCase):

    def setUp(self):
        self._called = False
        self._old_getppid = os.getppid
        os.getppid = mock_getppid

    def tearDown(self):
        os.getppid = self._old_getppid

    def orphan_callback(self):
        self._called = True

    def test_monitor(self):
        monitor = opm.OrphanProcessMonitor(callback=self.orphan_callback)
        monitor.start()

        time.sleep(1)
        self.assertTrue(self._called)

        monitor.stop()

if __name__ == "__main__":
    ut.main()
