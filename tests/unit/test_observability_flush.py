#
# Copyright 2026 Splunk Inc.
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
import threading
import time
from unittest.mock import MagicMock

from solnlib import _observability_flush as flushmod
from solnlib._observability_flush import _AsyncFlushController


def test_request_flush_returns_while_export_is_blocked():
    entered = threading.Event()
    release = threading.Event()
    provider = MagicMock()

    def blocked_flush(**kwargs):
        entered.set()
        assert release.wait(2)

    provider.force_flush.side_effect = blocked_flush
    controller = _AsyncFlushController(provider, MagicMock(spec=logging.Logger), str)
    try:
        start = time.monotonic()
        controller.request_flush(30_000)
        assert time.monotonic() - start < 0.2
        assert entered.wait(1)
        provider.force_flush.assert_called_once_with(timeout_millis=30_000)
    finally:
        release.set()
        controller.request_shutdown(time.monotonic() + 1)
        controller.join_until(time.monotonic() + 1)


def test_repeated_requests_during_export_coalesce_to_one_followup():
    entered = threading.Event()
    release = threading.Event()
    second_done = threading.Event()
    provider = MagicMock()

    def flush(**kwargs):
        if provider.force_flush.call_count == 1:
            entered.set()
            assert release.wait(2)
        else:
            second_done.set()

    provider.force_flush.side_effect = flush
    controller = _AsyncFlushController(provider, MagicMock(spec=logging.Logger), str)
    try:
        controller.request_flush(30_000)
        assert entered.wait(1)
        controller.request_flush(10_000)
        controller.request_flush(5_000)
        release.set()
        assert second_done.wait(1)
        assert provider.force_flush.call_count == 2
        assert provider.force_flush.call_args_list[-1].kwargs == {
            "timeout_millis": 5_000
        }
    finally:
        release.set()
        controller.request_shutdown(time.monotonic() + 1)
        controller.join_until(time.monotonic() + 1)


def test_worker_logs_export_error_without_raising_to_caller():
    logged = threading.Event()
    provider = MagicMock()
    provider.force_flush.side_effect = RuntimeError("boom")
    logger = MagicMock(spec=logging.Logger)
    logger.info.side_effect = lambda *args: logged.set()
    controller = _AsyncFlushController(provider, logger, str)
    try:
        controller.request_flush(30_000)
        assert logged.wait(1)
        assert "boom" in logger.info.call_args.args[-1]
    finally:
        controller.request_shutdown(time.monotonic() + 1)
        controller.join_until(time.monotonic() + 1)


def test_shutdown_is_once_and_later_flush_is_ignored():
    provider = MagicMock()
    controller = _AsyncFlushController(provider, MagicMock(spec=logging.Logger), str)
    deadline = time.monotonic() + 1
    controller.request_shutdown(deadline)
    controller.request_shutdown(deadline)
    controller.join_until(deadline)
    controller.request_flush(30_000)
    provider.shutdown.assert_called_once()
    provider.force_flush.assert_not_called()


def test_exit_budget_is_shared_by_two_controllers(monkeypatch):
    monkeypatch.setattr(flushmod, "_EXIT_GRACE_SECONDS", 0.05)
    release = threading.Event()
    entered = [threading.Event(), threading.Event()]
    controllers = []
    registry = flushmod._FlushRegistry()
    for gate in entered:
        provider = MagicMock()
        provider.shutdown.side_effect = lambda gate=gate, **kwargs: (
            gate.set(),
            release.wait(2),
        )
        controller = _AsyncFlushController(
            provider, MagicMock(spec=logging.Logger), str
        )
        registry._controllers.append(controller)
        controllers.append(controller)
    try:
        start = time.monotonic()
        registry.shutdown_all()
        assert time.monotonic() - start < 0.2
        assert all(gate.wait(1) for gate in entered)
    finally:
        release.set()
        for controller in controllers:
            controller.join_until(time.monotonic() + 1)


def test_one_atexit_registration_for_multiple_controllers(monkeypatch):
    register = MagicMock()
    monkeypatch.setattr(flushmod.atexit, "register", register)
    if hasattr(flushmod.os, "register_at_fork"):
        monkeypatch.setattr(flushmod.os, "register_at_fork", MagicMock())
    registry = flushmod._FlushRegistry()
    registry.add(MagicMock())
    registry.add(MagicMock())
    register.assert_called_once_with(flushmod._shutdown_all)
