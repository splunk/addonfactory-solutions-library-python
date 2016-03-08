import sys
import os
import os.path as op
import unittest
import threading
import multiprocessing
import time

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import splunksolutionlib.common.log as log


class TestLog(unittest.TestCase):

    def test_logging(self):
        logger = log.Logs().get_logger(
            'logging', directory='/tmp/', namespace='unittest')

        logger.debug('this is a test log')
        logger.warn('this is a test log that can show')

        os.remove('/tmp/unittest_logging.log')

    def test_enter_exit(self):
        logger1 = log.Logs().get_logger(
            'enter_exit1', directory='/tmp/', namespace='unittest')
        logger2 = log.Logs().get_logger(
            'enter_exit2', directory='/tmp/', namespace='unittest',
            level=log.logging.DEBUG)

        @log.log_enter_exit(logger1)
        def test1():
            pass

        @log.log_enter_exit(logger2)
        def test2():
            pass

        test1()
        test2()

        os.remove('/tmp/unittest_enter_exit1.log')
        os.remove('/tmp/unittest_enter_exit2.log')

    def test_set_level(self):
        logger = log.Logs().get_logger(
            'set_level', directory='/tmp/', namespace='unittest')

        logger.debug('this is a test log')

        log.Logs().set_level(log.logging.DEBUG)
        logger.warn('this is a test log that can show')

        log.Logs().set_level(log.logging.ERROR, name='set_level',
                             directory='/tmp/', namespace='unittest')
        logger.warn('this is a test log that can not show')

        os.remove('/tmp/unittest_set_level.log')

    def test_multi_thread(self):
        logger = log.Logs().get_logger(
            'test_multi_thread', directory='/tmp/',
            namespace='unittest', level=log.logging.DEBUG)

        logger.debug('Log info from main thread')

        def worker(logger_ref):
            native_logger = log.Logs().get_logger(
                'test_multi_thread', directory='/tmp/',
                namespace='unittest', level=log.logging.DEBUG)

            for i in range(100):
                logger_ref.debug('Log info from child thread')
                native_logger.debug(
                    'Log info from child thread on native logger')
                time.sleep(0.01)

        for i in range(20):
            t = threading.Thread(target=worker, args=(logger,))
            t.start()

        time.sleep(1)
        os.remove('/tmp/unittest_test_multi_thread.log')

    def test_multi_process(self):
        logger = log.Logs().get_logger(
            'test_multi_process', directory='/tmp/',
            namespace='unittest', level=log.logging.DEBUG)

        logger.debug('Log info from main process')

        def worker(logger_ref):
            native_logger = log.Logs().get_logger(
                'test_multi_process', directory='/tmp/',
                namespace='unittest', level=log.logging.DEBUG)

            for i in range(100):
                logger_ref.debug('Log info from child process')
                native_logger.debug(
                    'Log info from child process on native logger')
                time.sleep(0.01)

        for _ in range(20):
            p = multiprocessing.Process(target=worker, args=(logger,))
            p.start()

        time.sleep(1)
        os.remove('/tmp/unittest_test_multi_process.log')

if __name__ == '__main__':
    unittest.main(verbosity=2)
