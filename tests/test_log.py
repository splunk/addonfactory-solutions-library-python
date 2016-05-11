import sys
import os
import os.path as op
import threading
import multiprocessing
import time
import shutil

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import log


def setup_module(module):
    os.mkdir('./.log')
    log.Logs.set_context(directory='./.log', namespace='unittest')


def teardown_module(module):
    shutil.rmtree('./.log')


def test_log_enter_exit(monkeypatch):
    logger1 = log.Logs().get_logger('enter_exit1')
    logger2 = log.Logs().get_logger('enter_exit2')

    @log.log_enter_exit(logger1)
    def test1():
        pass

    @log.log_enter_exit(logger2)
    def test2():
        pass

    test1()
    test2()


class TestLogs(object):

    def test_get_logger(self, monkeypatch):
        logger = log.Logs().get_logger('logging')

        logger.debug('this is a test log')
        logger.warn('this is a test log that can show')

    def test_set_level(self, monkeypatch):
        logger = log.Logs().get_logger('set_level')

        logger.debug('this is a test log')

        log.Logs().set_level(log.logging.DEBUG)
        logger.warn('this is a test log that can show')

        log.Logs().set_level(log.logging.ERROR, name='set_level')
        logger.warn('this is a test log that can not show')

    def test_multi_thread(self, monkeypatch):
        log.Logs.set_context(directory='/tmp/', namespace='unittest')
        logger = log.Logs().get_logger('test_multi_thread')

        logger.debug('Log info from main thread')

        def worker(logger_ref):
            native_logger = log.Logs().get_logger(
                'test_multi_thread')

            for i in range(100):
                logger_ref.debug('Log info from child thread')
                native_logger.debug(
                    'Log info from child thread on native logger')

        for i in range(20):
            t = threading.Thread(target=worker, args=(logger,))
            t.start()

        time.sleep(1)

    def test_multi_process(self, monkeypatch):
        log.Logs.set_context(directory='/tmp/', namespace='unittest')
        logger = log.Logs().get_logger('test_multi_process')

        logger.debug('Log info from main process')

        def worker(logger_ref):
            native_logger = log.Logs().get_logger('test_multi_process')

            for i in range(100):
                logger_ref.debug('Log info from child process')
                native_logger.debug(
                    'Log info from child process on native logger')

        for _ in range(20):
            p = multiprocessing.Process(target=worker, args=(logger,))
            p.start()

        time.sleep(1)
