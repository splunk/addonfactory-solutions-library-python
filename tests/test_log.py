import sys
import os
import os.path as op
import unittest
import threading
import multiprocessing
import time

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.common import log
from splunksolutionlib.platform.platform import make_splunkhome_path


class TestLog(unittest.TestCase):

    def test_logging(self):
        logger = log.Logs(namespace='unittest').get_logger('logging')

        logger.debug('this is a test log')
        logger.warn('this is a test log that can show')

        os.remove(make_splunkhome_path(['var', 'log', 'splunk',
                                        'unittest_logging.log']))

    def test_enter_exit(self):
        logger1 = log.Logs(namespace='unittest').get_logger('enter_exit1')
        logger2 = log.Logs(namespace='unittest').get_logger('enter_exit2',
                                                            level='DEBUG')

        @log.log_enter_exit(logger1)
        def test1():
            pass

        @log.log_enter_exit(logger2)
        def test2():
            pass

        test1()
        test2()

        os.remove(make_splunkhome_path(['var', 'log', 'splunk',
                                        'unittest_enter_exit1.log']))
        os.remove(make_splunkhome_path(['var', 'log', 'splunk',
                                        'unittest_enter_exit2.log']))

    def test_set_level(self):
        logger = log.Logs(namespace='unittest').get_logger('set_level')

        logger.debug('this is a test log')

        log.Logs().set_level(log.logging.DEBUG)
        logger.warn('this is a test log that can show')

        log.Logs().set_level(log.logging.ERROR, name='set_level')
        logger.warn('this is a test log that can not show')

        os.remove(make_splunkhome_path(['var', 'log', 'splunk',
                                        'unittest_set_level.log']))

    def test_multi_thread(self):
        logger = log.Logs(namespace='unittest').get_logger(
            'test_multi_thread', level='DEBUG')

        logger.debug('Log info from main thread')

        def worker(logger_ref):
            native_logger = log.Logs(namespace='unittest').get_logger(
                'test_multi_thread', level='DEBUG')

            for i in range(100):
                logger_ref.debug('Log info from child thread')
                native_logger.debug(
                    'Log info from child thread on native logger')
                time.sleep(0.01)

        for i in range(20):
            t = threading.Thread(target=worker, args=(logger,))
            t.start()

        time.sleep(1)
        os.remove(make_splunkhome_path(['var', 'log', 'splunk',
                                        'unittest_test_multi_thread.log']))

    def test_multi_process(self):
        logger = log.Logs(namespace='unittest').get_logger(
            'test_multi_process', level='DEBUG')

        logger.debug('Log info from main process')

        def worker(logger_ref):
            native_logger = log.Logs(namespace='unittest').get_logger(
                'test_multi_process', level='DEBUG')

            for _ in range(100):
                logger_ref.debug('Log info from child process')
                native_logger.debug(
                    'Log info from child process on native logger')
                time.sleep(0.01)

        for _ in range(20):
            p = multiprocessing.Process(target=worker, args=(logger,))
            p.start()

        time.sleep(1)
        os.remove(make_splunkhome_path(['var', 'log', 'splunk',
                                        'unittest_test_multi_process.log']))

if __name__ == '__main__':
    unittest.main()
