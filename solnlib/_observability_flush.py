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
"""Private background worker for OpenTelemetry metric flush and shutdown."""

import atexit
import os
import threading
import time
from typing import Callable, Optional

_EXIT_GRACE_SECONDS = 5.0


def _remaining_ms(deadline: float) -> int:
    return max(0, int((deadline - time.monotonic()) * 1000))


class _AsyncFlushController:
    """Serialize one provider's explicit flushes and final shutdown."""

    def __init__(
        self, provider, logger, format_error: Callable[[BaseException], str]
    ) -> None:
        self._provider = provider
        self._logger = logger
        self._format_error = format_error
        self._condition = threading.Condition()
        self._pending_timeout = None
        self._shutdown_deadline = None
        self._worker = threading.Thread(
            target=self._run, name="SolnlibMetricFlush", daemon=True
        )
        self._worker.start()

    def request_flush(self, timeout_millis: float) -> None:
        with self._condition:
            if self._shutdown_deadline is None:
                self._pending_timeout = int(timeout_millis)
                self._condition.notify()

    def request_shutdown(self, deadline: float) -> None:
        with self._condition:
            if self._shutdown_deadline is None:
                self._shutdown_deadline = deadline
                self._condition.notify()

    def join_until(self, deadline: float) -> None:
        self._worker.join(timeout=max(0.0, deadline - time.monotonic()))

    def _run(self) -> None:
        while True:
            flush_timeout, shutdown_deadline = self._wait_for_request()
            if shutdown_deadline is None:
                if flush_timeout is not None:
                    self._flush(flush_timeout)
                continue
            self._shut_down(flush_timeout, shutdown_deadline)
            return

    def _has_request(self) -> bool:
        return self._pending_timeout is not None or self._shutdown_deadline is not None

    def _wait_for_request(self) -> tuple[Optional[int], Optional[float]]:
        with self._condition:
            self._condition.wait_for(self._has_request)
            flush_timeout, self._pending_timeout = self._pending_timeout, None
            return flush_timeout, self._shutdown_deadline

    def _shut_down(self, flush_timeout: Optional[int], deadline: float) -> None:
        # Readers with an infinite export interval do not collect on shutdown.
        remaining = _remaining_ms(deadline)
        if flush_timeout is not None and remaining:
            self._flush(min(flush_timeout, remaining))
        try:
            self._provider.shutdown(timeout_millis=_remaining_ms(deadline))
        except Exception as error:
            self._logger.info(
                "Failed to shut down metrics: %s", self._format_error(error)
            )

    def _flush(self, timeout_ms: int) -> None:
        try:
            self._provider.force_flush(timeout_millis=timeout_ms)
        except Exception as error:
            self._logger.info("Failed to flush metrics: %s", self._format_error(error))

    def restart_after_fork(self) -> None:
        """Replace parent-thread state after fork in the child process."""
        self._condition = threading.Condition()
        self._pending_timeout = None
        self._shutdown_deadline = None
        self._worker = threading.Thread(
            target=self._run, name="SolnlibMetricFlush", daemon=True
        )
        self._worker.start()


class _FlushRegistry:
    """Coordinate all metric providers against one process-exit deadline."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._controllers = []
        self._registered = False
        self._closed = False

    def register(self, provider, logger, format_error) -> _AsyncFlushController:
        with self._lock:
            if self._closed:
                raise RuntimeError("Metrics shutdown has started")
            if not self._registered:
                atexit.register(_shutdown_all)
                if hasattr(os, "register_at_fork"):
                    os.register_at_fork(after_in_child=self._after_fork_child)
                self._registered = True
            controller = _AsyncFlushController(provider, logger, format_error)
            self._controllers.append(controller)
            return controller

    def shutdown_all(self) -> None:
        deadline = time.monotonic() + _EXIT_GRACE_SECONDS
        with self._lock:
            if self._closed:
                return
            self._closed = True
            controllers = tuple(self._controllers)
        for controller in controllers:
            controller.request_shutdown(deadline)
        for controller in controllers:
            controller.join_until(deadline)

    def _after_fork_child(self) -> None:
        self._lock = threading.Lock()
        if self._closed:
            return
        for controller in self._controllers:
            controller.restart_after_fork()


_registry = _FlushRegistry()


def _register_controller(provider, logger, format_error) -> _AsyncFlushController:
    return _registry.register(provider, logger, format_error)


def _shutdown_all() -> None:
    _registry.shutdown_all()
