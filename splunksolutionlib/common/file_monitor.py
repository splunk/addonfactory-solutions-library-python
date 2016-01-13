# Copyright (C) 2005-2016 Splunk Inc. All Rights Reserved.

import os.path as op
import traceback
import time
import threading

from splunksolutionlib.common import log

logger = log.Logs().get_logger("solutionlib")


class FileChangesChecker(object):

    def __init__(self, callback, files):
        """
        :files: files to be monidtored with full path
        """

        self._callback = callback
        self._files = files

        self.file_mtimes = {file_name: None for file_name in self._files}
        for k in self.file_mtimes:
            try:
                self.file_mtimes[k] = op.getmtime(k)
            except OSError:
                logger.debug("Getmtime for %s, failed: %s", k,
                             traceback.format_exc())

    def check_changes(self):
        logger.debug("Checking files=%s", self._files)
        file_mtimes = self.file_mtimes
        changed_files = []
        for f, last_mtime in file_mtimes.iteritems():
            try:
                current_mtime = op.getmtime(f)
                if current_mtime != last_mtime:
                    file_mtimes[f] = current_mtime
                    changed_files.append(f)
                    logger.info("Detect %s has changed", f)
            except OSError:
                pass

        if changed_files:
            if self._callback:
                self._callback(changed_files)
            return True
        return False


class FileMonitor(object):
    """
    Monitor file changes in a separated thread. Call callback when file changes
    """

    def __init__(self, callback, files, interval=10):
        """
        :callback: callable
        :files: tuple/list etc iteratable which contains absolute file paths
        :interval: check intervals in seconds
        """

        self._checker = FileChangesChecker(callback, files)
        self._thr = threading.Thread(target=self._do_monitor)
        self._thr.daemon = True
        self._interval = interval
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True

        self._thr.start()

    def stop(self):
        self._started = False

    def _do_monitor(self):
        while self._started:
            if self._checker.check_changes():
                break

            for _ in xrange(self._interval):
                if not self._started:
                    break
                time.sleep(1)
