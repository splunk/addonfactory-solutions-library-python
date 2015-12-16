import unittest
import os

import threading
import multiprocessing
import time

from splunksolutionlib.common import log


class TestLog(unittest.TestCase):

    def setUp(self):
        curdir = os.path.dirname(os.path.abspath(__file__))
        os.environ["SPLUNK_HOME"] = curdir
        namespace = "unittest"
        self.logger = log.Logs(namespace=namespace).get_logger("unitest")

    def tearDown(self):
        pass

    def test_logging(self):
        self.logger.debug("this is a test log")
        self.logger.warn("this is a test log that can show")

    def test_enter_exit(self):

        logger1 = log.Logs().get_logger("unitest1", level="DEBUG")

        @log.log_enter_exit(self.logger)
        def test():
            pass

        @log.log_enter_exit(logger1)
        def test1():
            pass

        test()
        test1()

    def test_multi_thread(self):
        logger = log.Logs().get_logger("test_multi_thread", level="DEBUG")

        logger.debug("Log info from main thread")

        def worker(logger_ref):
            native_logger = log.Logs().get_logger(
                "test_multi_thread", level="DEBUG")
            for i in range(100):
                logger_ref.debug("Log info from child thread")
                native_logger.debug(
                    "Log info from child thread on native logger")
                time.sleep(0.01)

        for i in range(20):
            t = threading.Thread(target=worker, args=(logger,))
            t.start()

    def test_multi_process(self):
        logger = log.Logs().get_logger("test_multi_process", level="DEBUG")

        logger.debug("Log info from main process")

        def worker(logger_ref):
            native_logger = log.Logs().get_logger(
                "test_multi_process", level="DEBUG")

            for _ in range(100):
                logger_ref.debug("Log info from child process")
                native_logger.debug(
                    "Log info from child process on native logger")
                time.sleep(0.01)

        for _ in range(20):
            p = multiprocessing.Process(target=worker, args=(logger,))
            p.start()

if __name__ == "__main__":
    unittest.main()
