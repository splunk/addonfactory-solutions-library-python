import os
import signal
import unittest as ut
import multiprocessing
import time

from splunksolutionlib.common import orphan_process_monitor as opm


class TestOrphanProcessMonitor(ut.TestCase):

    def setUp(self):
        self._child = multiprocessing.Process(target=self._child_func)
        self._child.start()
        self._called = False
        time.sleep(1)

    def orphan_callback(self):
        self._called = True

    def _child_func(self):
        monitor = opm.OrphanProcessMonitor(callback=self.orphan_callback)
        monitor.start()
        time.sleep(3)
        self.assertTrue(self._called)

    def test_monitor(self):
        p = multiprocessing.current_process()
        # Kill myself to make the child orphan
        os.kill(p.ident, signal.SIGTERM)


if __name__ == "__main__":
    ut.main()
