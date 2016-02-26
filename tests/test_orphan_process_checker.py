import sys
import os
import os.path as op
import signal
import unittest as ut
import multiprocessing
import time

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.common import orphan_process_monitor as opm


class TestOrphanProcessChecker(ut.TestCase):

    def setUp(self):
        self._called = False
        multiprocessing.Process(target=self._child_func).start()

    def orphan_callback(self):
        self._called = True

    def _child_func(self):
        checker = opm.OrphanProcessChecker(callback=self.orphan_callback)
        time.sleep(4)
        res = checker.is_orphan()
        self.assertTrue(res)
        res = checker.check_orphan()
        self.assertTrue(res)
        self.assertTrue(self._called)

    def test_is_orphan(self):
        time.sleep(1)
        p = multiprocessing.current_process()
        # Kill myself to make the child orphan
        os.kill(p.ident, signal.SIGTERM)

if __name__ == "__main__":
    ut.main()
