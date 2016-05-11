import sys
import os
import os.path as op
import time
import random

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import orphan_process_monitor as opm


def _mock_getppid():
    return random.randint(1, 65535)


class TestOrphanProcessChecker(object):

    def setup(self):
        self._called = False

    def test_is_orphan(self, monkeypatch):
        monkeypatch.setattr(os, 'getppid', _mock_getppid)

        def orphan_callback():
            self._called = True

        checker = opm.OrphanProcessChecker(callback=orphan_callback)
        res = checker.is_orphan()
        assert res
        res = checker.check_orphan()
        assert res
        assert self._called


class TestOrphanProcessMonitor(object):

    def setup(self):
        self._called = False

    def test_monitor(self, monkeypatch):
        monkeypatch.setattr(os, 'getppid', _mock_getppid)

        def orphan_callback():
            self._called = True

        monitor = opm.OrphanProcessMonitor(callback=orphan_callback)
        monitor.start()

        time.sleep(1)
        assert self._called

        monitor.stop()
