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

import pytest
from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult

from solnlib import _observability_flush as flushmod
from solnlib._observability_flush import _AsyncFlushController
from solnlib.observability import ObservabilityService


@pytest.fixture
def controller_factory():
    controllers = []

    def create(provider, logger=None):
        controller = _AsyncFlushController(
            provider, logger or MagicMock(spec=logging.Logger), str
        )
        controllers.append(controller)
        return controller

    yield create

    deadline = time.monotonic() + 1
    for controller in controllers:
        controller.request_shutdown(deadline)
    for controller in controllers:
        controller.join_until(deadline)


@pytest.fixture
def registry_and_callbacks(monkeypatch):
    registry = flushmod._FlushRegistry()
    callbacks = []

    def register_callback(callback):
        callbacks.append(callback)
        return callback

    monkeypatch.setattr(flushmod, "_registry", registry)
    monkeypatch.setattr(flushmod.atexit, "register", register_callback)
    if hasattr(flushmod.os, "register_at_fork"):
        monkeypatch.setattr(flushmod.os, "register_at_fork", MagicMock())

    yield registry, callbacks

    registry.shutdown_all()


def test_request_flush_returns_while_export_is_blocked(controller_factory):
    # Arrange
    entered = threading.Event()
    release = threading.Event()
    provider = MagicMock()

    def blocked_flush(**kwargs):
        entered.set()
        release.wait()

    provider.force_flush.side_effect = blocked_flush
    controller = controller_factory(provider)
    try:
        # Act
        start = time.monotonic()
        controller.request_flush(30_000)
        elapsed = time.monotonic() - start
        export_started = entered.wait(1)

        # Assert
        assert elapsed < 0.2
        assert export_started
        provider.force_flush.assert_called_once_with(timeout_millis=30_000)
    finally:
        release.set()


def test_repeated_requests_during_export_coalesce_to_one_followup(controller_factory):
    # Arrange
    entered = threading.Event()
    release = threading.Event()
    second_done = threading.Event()
    provider = MagicMock()

    def flush(**kwargs):
        if provider.force_flush.call_count == 1:
            entered.set()
            release.wait()
        else:
            second_done.set()

    provider.force_flush.side_effect = flush
    controller = controller_factory(provider)
    try:
        # Act
        controller.request_flush(30_000)
        first_started = entered.wait(1)
        controller.request_flush(10_000)
        controller.request_flush(5_000)
        release.set()
        followup_finished = second_done.wait(1)

        # Assert
        assert first_started
        assert followup_finished
        assert provider.force_flush.call_count == 2
        assert provider.force_flush.call_args_list[-1].kwargs == {
            "timeout_millis": 5_000
        }
    finally:
        release.set()


def test_worker_logs_export_error_without_raising_to_caller(controller_factory):
    # Arrange
    logged = threading.Event()
    provider = MagicMock()
    provider.force_flush.side_effect = RuntimeError("boom")
    logger = MagicMock(spec=logging.Logger)
    logger.info.side_effect = lambda *args: logged.set()
    controller = controller_factory(provider, logger)

    # Act
    controller.request_flush(30_000)
    error_logged = logged.wait(1)

    # Assert
    assert error_logged
    assert "boom" in logger.info.call_args.args[-1]


def test_shutdown_is_once_and_later_flush_is_ignored(controller_factory):
    # Arrange
    provider = MagicMock()
    controller = controller_factory(provider)
    deadline = time.monotonic() + 1

    # Act
    controller.request_shutdown(deadline)
    controller.request_shutdown(deadline)
    controller.join_until(deadline)
    controller.request_flush(30_000)

    # Assert
    provider.shutdown.assert_called_once()
    provider.force_flush.assert_not_called()
    assert not controller._worker.is_alive()


def test_exit_budget_is_shared_by_two_controllers(monkeypatch, registry_and_callbacks):
    # Arrange
    monkeypatch.setattr(flushmod, "_EXIT_GRACE_SECONDS", 0.05)
    registry, _ = registry_and_callbacks
    release = threading.Event()
    entered = [threading.Event(), threading.Event()]
    controllers = []
    for gate in entered:
        provider = MagicMock()
        provider.shutdown.side_effect = lambda gate=gate, **kwargs: (
            gate.set(),
            release.wait(),
        )
        controllers.append(registry.register(provider, MagicMock(), str))
    try:
        # Act
        start = time.monotonic()
        registry.shutdown_all()
        elapsed = time.monotonic() - start

        # Assert
        assert elapsed < 0.2
        assert all(gate.wait(1) for gate in entered)
    finally:
        release.set()
        for controller in controllers:
            controller.join_until(time.monotonic() + 1)


def test_one_atexit_registration_for_multiple_controllers(registry_and_callbacks):
    # Arrange
    registry, callbacks = registry_and_callbacks

    # Act
    registry.register(MagicMock(), MagicMock(), str)
    registry.register(MagicMock(), MagicMock(), str)

    # Assert
    assert callbacks == [flushmod._shutdown_all]


def test_closed_registry_does_not_start_a_worker(monkeypatch, registry_and_callbacks):
    # Arrange
    registry, _ = registry_and_callbacks
    registry.shutdown_all()
    controller_cls = MagicMock()
    monkeypatch.setattr(flushmod, "_AsyncFlushController", controller_cls)

    # Act
    with pytest.raises(RuntimeError, match="shutdown has started"):
        flushmod._register_controller(MagicMock(), MagicMock(), str)

    # Assert
    controller_cls.assert_not_called()
    assert registry._controllers == []


def test_closed_registry_does_not_restart_workers_after_fork(registry_and_callbacks):
    # Arrange
    registry, _ = registry_and_callbacks
    controller = registry.register(MagicMock(), MagicMock(), str)
    registry.shutdown_all()
    original_worker = controller._worker
    try:
        # Act
        registry._after_fork_child()

        # Assert
        assert controller._worker is original_worker
        assert not controller._worker.is_alive()
    finally:
        deadline = time.monotonic() + 1
        controller.request_shutdown(deadline)
        controller.join_until(deadline)


def test_exit_handler_cannot_register_a_worker_after_registry_shutdown(
    registry_and_callbacks,
):
    # Arrange
    registry, callbacks = registry_and_callbacks
    registration_errors = []

    def late_handler():
        try:
            flushmod._register_controller(MagicMock(), MagicMock(), str)
        except RuntimeError as error:
            registration_errors.append(error)

    callbacks.append(late_handler)
    controller = flushmod._register_controller(MagicMock(), MagicMock(), str)

    # Act
    for callback in reversed(callbacks):
        callback()

    # Assert
    assert len(registration_errors) == 1
    assert registry._controllers == [controller]
    assert not controller._worker.is_alive()


def test_registered_exit_callback_attempts_shutdown_without_explicit_flush(
    registry_and_callbacks,
):
    # Arrange
    _, callbacks = registry_and_callbacks
    provider = MagicMock()
    controller = flushmod._register_controller(provider, MagicMock(), str)

    # Act
    callbacks[0]()

    # Assert
    provider.shutdown.assert_called_once()
    assert not controller._worker.is_alive()


def test_shutdown_exports_pending_flush_without_periodic_reader(
    monkeypatch, registry_and_callbacks
):
    # Arrange
    monkeypatch.setenv("OTEL_METRIC_EXPORT_INTERVAL", "inf")
    monkeypatch.setattr(
        ObservabilityService, "_create_otlp_exporter", lambda self: None
    )
    entered = threading.Event()
    release = threading.Event()
    exported_values = []

    class RecordingExporter(MetricExporter):
        def export(self, metrics_data, timeout_millis=10_000, **kwargs):
            value = sum(
                point.value
                for resource in metrics_data.resource_metrics
                for scope in resource.scope_metrics
                for metric in scope.metrics
                if metric.name == "splunk.addon.events"
                for point in metric.data.data_points
            )
            exported_values.append(value)
            if len(exported_values) == 1:
                entered.set()
                release.wait()
            return MetricExportResult.SUCCESS

        def shutdown(self, timeout_millis=30_000, **kwargs):
            pass

        def force_flush(self, timeout_millis=10_000):
            return True

    service = ObservabilityService(
        "test-input",
        MagicMock(spec=logging.Logger),
        ta_name="test-ta",
        ta_version="1.0.0",
        extra_exporters=[RecordingExporter()],
    )
    try:
        # Act
        service.event_count_counter.add(1)
        service.flush()
        first_export_started = entered.wait(1)
        service.event_count_counter.add(2)
        service.flush()
        deadline = time.monotonic() + 1
        service._flush_controller.request_shutdown(deadline)
        release.set()
        service._flush_controller.join_until(deadline)

        # Assert
        assert first_export_started
        assert exported_values == [1, 3]
        assert not service._flush_controller._worker.is_alive()
    finally:
        release.set()
