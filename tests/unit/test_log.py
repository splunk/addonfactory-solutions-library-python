#
# Copyright 2023 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import json
import multiprocessing
import os
import shutil
import threading
import traceback
import time
from unittest import mock

from solnlib import log

reset_root_log_path = os.path.join(".", ".root_log")


def setup_module(module):
    if os.path.isdir("./.log"):
        shutil.rmtree("./.log")
    os.mkdir("./.log")
    log.Logs.set_context(directory="./.log", namespace="unittest")
    if os.path.isdir(reset_root_log_path):
        shutil.rmtree(reset_root_log_path)
    os.mkdir(reset_root_log_path)


def teardown_module(module):
    shutil.rmtree("./.log")
    shutil.rmtree(reset_root_log_path)


def test_log_enter_exit(monkeypatch):
    logger1 = log.Logs().get_logger("enter_exit1")
    logger2 = log.Logs().get_logger("enter_exit2")

    @log.log_enter_exit(logger1)
    def test1():
        pass

    @log.log_enter_exit(logger2)
    def test2():
        pass

    test1()
    test2()


class TestLogs:
    def test_get_logger(self, monkeypatch):
        logger = log.Logs().get_logger("logging")

        logger.debug("this is a test log")
        logger.warning("this is a test log that can show")

    def test_set_level(self, monkeypatch):
        logger = log.Logs().get_logger("set_level")

        logger.debug("this is a test log")

        log.Logs().set_level(log.logging.DEBUG)
        logger.warning("this is a test log that can show")

        log.Logs().set_level(log.logging.ERROR, name="set_level")
        logger.warning("this is a test log that can not show")

    def test_multi_thread(self, monkeypatch):
        log.Logs.set_context(directory="/tmp/", namespace="unittest")
        logger = log.Logs().get_logger("test_multi_thread")

        logger.debug("Log info from main thread")

        def worker(logger_ref):
            native_logger = log.Logs().get_logger("test_multi_thread")

            for i in range(100):
                logger_ref.debug("Log info from child thread")
                native_logger.debug("Log info from child thread on native logger")

        for i in range(20):
            t = threading.Thread(target=worker, args=(logger,))
            t.start()

        time.sleep(1)

    def test_multi_process(self, monkeypatch):
        log.Logs.set_context(directory="/tmp/", namespace="unittest")
        logger = log.Logs().get_logger("test_multi_process")

        logger.debug("Log info from main process")

        def worker(logger_ref):
            native_logger = log.Logs().get_logger("test_multi_process")

            for i in range(100):
                logger_ref.debug("Log info from child process")
                native_logger.debug("Log info from child process on native logger")

        for _ in range(20):
            p = multiprocessing.Process(target=worker, args=(logger,))
            p.start()

        time.sleep(1)

    def test_set_root_log_file(self, monkeypatch):
        log.Logs.set_context(directory=reset_root_log_path, namespace="unittest")
        default_root_log_file = os.path.join(
            reset_root_log_path, "{}_{}.log".format("unittest", "solnlib")
        )
        assert not os.path.isfile(default_root_log_file)
        logging.info("This is a INFO log in root logger.")
        logging.error("This is a ERROR log in root logger.")
        assert not os.path.isfile(default_root_log_file)  # reset is not called yet.

        root_log_file = os.path.join(
            reset_root_log_path, "{}_{}.log".format("unittest", "my_root")
        )
        assert not os.path.isfile(root_log_file)
        log.Logs.set_context(
            directory=reset_root_log_path,
            namespace="unittest",
            root_logger_log_file="my_root",
        )
        logging.info("This is another INFO log in root logger.")
        logging.error("This is another ERROR log in root logger.")
        assert os.path.isfile(root_log_file)


def test_log_event():
    with mock.patch("logging.Logger") as mock_logger:
        log.log_event(
            mock_logger,
            {
                "key": "foo",
                "value": "bar",
            },
        )

        mock_logger.log.assert_called_once_with(logging.INFO, "key=foo value=bar")


def test_log_event_when_debug_log_level():
    with mock.patch("logging.Logger") as mock_logger:
        log.log_event(
            mock_logger,
            {
                "key": "foo",
                "value": "bar",
            },
            log_level=logging.DEBUG,
        )

        mock_logger.log.assert_called_once_with(logging.DEBUG, "key=foo value=bar")


def test_modular_input_start():
    with mock.patch("logging.Logger") as mock_logger:
        log.modular_input_start(
            mock_logger,
            "modular_input_name",
        )

        mock_logger.log.assert_called_once_with(
            logging.INFO, "action=started modular_input_name=modular_input_name"
        )


def test_modular_input_end():
    with mock.patch("logging.Logger") as mock_logger:
        log.modular_input_end(
            mock_logger,
            "modular_input_name",
        )

        mock_logger.log.assert_called_once_with(
            logging.INFO, "action=ended modular_input_name=modular_input_name"
        )


def test_events_ingested():
    with mock.patch("logging.Logger") as mock_logger:
        log.events_ingested(mock_logger, "modular_input_name", "sourcetype", 5)

        mock_logger.log.assert_called_once_with(
            logging.INFO,
            "action=events_ingested modular_input_name=modular_input_name sourcetype_ingested=sourcetype n_events=5",
        )


def test_log_exceptions_full_msg():
    start_msg = "some msg before exception"
    with mock.patch("logging.Logger") as mock_logger:
        try:
            test_jsons = "{'a': 'aa'"
            json.loads(test_jsons)
        except Exception as e:
            log.log_exception(mock_logger, e, msg_before=start_msg)
            mock_logger.log.assert_called_with(
                logging.INFO, f"{start_msg}\n{traceback.format_exc()}\n"
            )


def test_log_exceptions_partial_msg():
    start_msg = "some msg before exception"
    end_msg = "some msg after exception"
    with mock.patch("logging.Logger") as mock_logger:
        try:
            test_jsons = "{'a': 'aa'"
            json.loads(test_jsons)
        except Exception as e:
            log.log_exception(
                mock_logger, e, full_msg=False, msg_before=start_msg, msg_after=end_msg
            )
            mock_logger.log.assert_called_with(
                logging.INFO,
                "some msg before exception\njson.decoder.JSONDecodeError: Expecting property name enclosed in double "
                "quotes: line 1 column 2 (char 1)\n\nsome msg after exception",
            )
