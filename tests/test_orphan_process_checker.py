import os
import signal
import unittest as ut
import multiprocessing
import time

from splunksolutionlib.common import orphan_process_monitor as opm


class TestOrphanProcessChecker(ut.TestCase):

    def setUp(self):
        self._child = multiprocessing.Process(target=self._child_func)
        self._child.start()
        self._called = False
        time.sleep(1)

    def orphan_callback(self):
        self._called = True

    def _child_func(self):
        checker = opm.OrphanProcessChecker(callback=self.orphan_callback)
        time.sleep(2)
        res = checker.is_orphan()
        self.assertTrue(res)
        res = checker.check_orphan()
        self.assertTrue(res)
        self.assertTrue(self._called)

    def test_is_orphan(self):
        p = multiprocessing.current_process()
        # Kill myself to make the child orphan
        os.kill(p.ident, signal.SIGTERM)


if __name__ == "__main__":
    ut.main()
