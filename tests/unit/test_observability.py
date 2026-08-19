#
# Copyright 2025 Splunk Inc.
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

import contextlib
import io
import logging
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.metrics import Counter, Histogram
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    PeriodicExportingMetricReader,
)

from solnlib.observability import LoggerMetricExporter, ObservabilityService


_GRPC_TLS_HANDSHAKE_SCRIPT = """
import sys
import grpc
from concurrent import futures

server_key_path, server_crt_path, wrong_root_path = sys.argv[1:4]

with open(server_key_path, "rb") as f:
    server_key = f.read()
with open(server_crt_path, "rb") as f:
    server_cert = f.read()
with open(wrong_root_path, "rb") as f:
    wrong_root = f.read()

server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
server_creds = grpc.ssl_server_credentials([(server_key, server_cert)])
port = server.add_secure_port("127.0.0.1:0", server_creds)
server.start()

client_creds = grpc.ssl_channel_credentials(root_certificates=wrong_root)
channel = grpc.secure_channel(f"127.0.0.1:{port}", client_creds)
try:
    grpc.channel_ready_future(channel).result(timeout=3)
except Exception:
    pass
finally:
    channel.close()
    server.stop(0)
"""


@pytest.fixture
def logger():
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def real_logger():
    """A real Logger + StreamHandler over a UTF-8 TextIOWrapper.

    MagicMock does not execute lazy `%`-formatting and StringIO does not
    perform UTF-8 encoding, so tests that must prove formatting/encoding
    never raises need a real logger.
    """
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="strict")
    handler = logging.StreamHandler(stream)
    test_logger = logging.getLogger("test.solnlib.observability.real")
    test_logger.setLevel(logging.DEBUG)
    test_logger.handlers = [handler]
    test_logger.propagate = False
    yield test_logger, stream
    test_logger.handlers = []


@contextlib.contextmanager
def _clean_logger_filters(*logger_names):
    """Snapshot each logger's filters, clear them for a clean-slate
    precondition, then restore the exact original list afterward —
    regardless of what the wrapped code attaches or removes."""
    loggers = [logging.getLogger(name) for name in logger_names]
    original = [list(lg.filters) for lg in loggers]
    for lg in loggers:
        lg.filters = []
    try:
        yield loggers
    finally:
        for lg, filters in zip(loggers, original):
            lg.filters = filters


# ---------------------------------------------------------------------------
# Safe log rendering
# ---------------------------------------------------------------------------


class _RaisesOnStr:
    def __str__(self):
        raise RuntimeError("boom")


class _BadExceptionRepr(Exception):
    def __repr__(self):
        raise RuntimeError("bad repr")

    def __str__(self):
        raise RuntimeError("bad str")


class _WeirdStr(str):
    def __str__(self):
        return "overridden!"


class TestSafeRendering:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("plain safe text", "plain safe text"),
            ("line1\r\nline2", "line1 line2"),
            ("line1\nline2", "line1 line2"),
            ("line1\rline2", "line1 line2"),
            ("\ud800", "?"),
        ],
    )
    def test_sanitize_for_log_plain_cases(self, value, expected):
        from solnlib.observability import _sanitize_for_log

        assert _sanitize_for_log(value) == expected

    def test_sanitize_for_log_truncates_long_text(self):
        from solnlib.observability import _sanitize_for_log

        result = _sanitize_for_log("x" * 600)
        assert result == "x" * 500 + "...(truncated)"

    def test_sanitize_for_log_non_string_raising_str(self):
        from solnlib.observability import _sanitize_for_log

        assert _sanitize_for_log(_RaisesOnStr()) == "<unrepresentable>"

    def test_sanitize_for_log_str_subclass_returns_plain_str(self):
        from solnlib.observability import _sanitize_for_log

        result = _sanitize_for_log(_WeirdStr("hello"))
        assert result == "hello"
        assert type(result) is str

    def test_safe_exception_repr_normal_exception(self):
        from solnlib.observability import _safe_exception_repr

        error = ValueError("bad value")
        assert _safe_exception_repr(error) == repr(error)

    def test_safe_exception_repr_falls_back_when_repr_raises(self):
        from solnlib.observability import _safe_exception_repr

        result = _safe_exception_repr(_BadExceptionRepr("x"))
        assert result == "_BadExceptionRepr (repr unavailable)"

    def test_safe_exception_str_normal_exception(self):
        from solnlib.observability import _safe_exception_str

        error = ValueError("bad value")
        assert _safe_exception_str(error) == str(error)

    def test_safe_exception_str_falls_back_when_str_raises(self):
        from solnlib.observability import _safe_exception_str

        result = _safe_exception_str(_BadExceptionRepr("x"))
        assert result == "_BadExceptionRepr (details unavailable)"

    def test_safe_exception_str_end_to_end_through_real_logger(
        self, real_logger, capsys
    ):
        from solnlib.observability import _safe_exception_str

        test_logger, stream = real_logger
        error = ValueError("multi\r\nline\r\nmessage")
        test_logger.info("boom: %s", _safe_exception_str(error))
        stream.flush()
        stream.seek(0)
        output = stream.read()
        assert "\n" not in output.strip("\n")
        assert "boom: multi line message" in output

        # logging.Handler.handleError() writes "--- Logging error ---" to the
        # real sys.stderr directly, never to the handler's own stream, so a
        # formatting/encoding failure must be detected there, not in `stream`.
        captured = capsys.readouterr()
        assert "--- Logging error ---" not in captured.err


# ---------------------------------------------------------------------------
# LoggerMetricExporter
# ---------------------------------------------------------------------------


def _make_counter_data_point(name, value, unit="1", attributes=None):
    """Build a minimal MetricsData stub with a single counter data point."""
    data_point = MagicMock()
    data_point.value = value
    data_point.attributes = attributes
    # No bucket_counts → counter path
    del data_point.bucket_counts

    metric = MagicMock()
    metric.name = name
    metric.unit = unit
    metric.data.data_points = [data_point]

    scope_metrics = MagicMock()
    scope_metrics.metrics = [metric]

    resource_metrics = MagicMock()
    resource_metrics.scope_metrics = [scope_metrics]

    metrics_data = MagicMock()
    metrics_data.resource_metrics = [resource_metrics]
    return metrics_data


def _make_histogram_data_point(name, unit="s"):
    """Build a minimal MetricsData stub with a single histogram data point."""
    data_point = MagicMock()
    data_point.count = 5
    data_point.sum = 10.0
    data_point.min = 1.0
    data_point.max = 3.0
    data_point.bucket_counts = [1, 2, 2]
    data_point.explicit_bounds = [1.0, 2.0]
    data_point.attributes = {"key": "val"}

    metric = MagicMock()
    metric.name = name
    metric.unit = unit
    metric.data.data_points = [data_point]

    scope_metrics = MagicMock()
    scope_metrics.metrics = [metric]

    resource_metrics = MagicMock()
    resource_metrics.scope_metrics = [scope_metrics]

    metrics_data = MagicMock()
    metrics_data.resource_metrics = [resource_metrics]
    return metrics_data


class TestLoggerMetricExporter:
    def test_export_counter_returns_success(self, logger):
        # Arrange
        exporter = LoggerMetricExporter(logger)
        # Act
        result = exporter.export(_make_counter_data_point("my.metric", 42))
        # Assert
        assert result == MetricExportResult.SUCCESS

    def test_export_counter_logs_value(self, logger):
        # Arrange
        exporter = LoggerMetricExporter(logger)
        # Act
        exporter.export(_make_counter_data_point("my.metric", 7, attributes={"a": "b"}))
        # Assert
        logger.info.assert_called()
        call_args = logger.info.call_args[0]
        assert "my.metric" in call_args[1]

    def test_export_counter_no_attributes(self, logger):
        # Arrange
        exporter = LoggerMetricExporter(logger)
        # Act
        result = exporter.export(
            _make_counter_data_point("my.metric", 1, attributes=None)
        )
        # Assert
        assert result == MetricExportResult.SUCCESS

    def test_export_histogram_returns_success(self, logger):
        # Arrange
        exporter = LoggerMetricExporter(logger)
        # Act
        result = exporter.export(_make_histogram_data_point("my.histogram"))
        # Assert
        assert result == MetricExportResult.SUCCESS

    def test_export_histogram_logs_bucket_info(self, logger):
        # Arrange
        exporter = LoggerMetricExporter(logger)
        # Act
        exporter.export(_make_histogram_data_point("my.histogram"))
        # Assert
        logger.info.assert_called()
        call_args = logger.info.call_args[0]
        assert "my.histogram" in call_args[1]

    def test_export_empty_metrics_data(self, logger):
        # Arrange
        metrics_data = MagicMock()
        metrics_data.resource_metrics = []
        exporter = LoggerMetricExporter(logger)
        # Act
        result = exporter.export(metrics_data)
        # Assert
        assert result == MetricExportResult.SUCCESS
        logger.debug.assert_not_called()

    def test_export_returns_failure_on_exception(self, logger):
        # Arrange
        metrics_data = MagicMock()
        metrics_data.resource_metrics.__iter__ = MagicMock(
            side_effect=RuntimeError("boom")
        )
        exporter = LoggerMetricExporter(logger)
        # Act
        result = exporter.export(metrics_data)
        # Assert
        assert result == MetricExportResult.FAILURE
        logger.info.assert_called()
        logger.error.assert_not_called()

    def test_shutdown_does_not_raise(self, logger):
        # Arrange / Act / Assert
        LoggerMetricExporter(logger).shutdown()

    def test_force_flush_returns_true(self, logger):
        # Arrange / Act / Assert
        assert LoggerMetricExporter(logger).force_flush() is True


# ---------------------------------------------------------------------------
# _CircuitBreakerExporter
# ---------------------------------------------------------------------------


class _FakeInnerExporter(MetricExporter):
    """Real MetricExporter subclass for deterministic circuit-breaker tests."""

    def __init__(self, temporality=None, aggregation=None):
        super().__init__(
            preferred_temporality=temporality
            or {
                Counter: AggregationTemporality.DELTA,
                Histogram: AggregationTemporality.DELTA,
            },
            preferred_aggregation=aggregation or {},
        )
        self.results = []  # queue of MetricExportResult values or Exception instances
        self.export_calls = []
        self.force_flush_calls = []
        self.shutdown_calls = []

    def export(self, metrics_data, timeout_millis=10_000, **kwargs):
        self.export_calls.append((metrics_data, timeout_millis, kwargs))
        outcome = self.results.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def force_flush(self, timeout_millis=10_000):
        self.force_flush_calls.append(timeout_millis)
        return True

    def shutdown(self, timeout_millis=30_000, **kwargs):
        self.shutdown_calls.append((timeout_millis, kwargs))


class TestCircuitBreakerExporter:
    def test_preserves_preferred_temporality_and_aggregation(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        temporality = {Counter: AggregationTemporality.DELTA}
        aggregation = {"some": "aggregation"}
        inner = _FakeInnerExporter(temporality, aggregation)
        wrapper = _CircuitBreakerExporter(inner, logger)
        assert wrapper._preferred_temporality == temporality
        assert wrapper._preferred_aggregation == aggregation

    def test_real_reader_reads_temporality_from_wrapper(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        temporality = {
            Counter: AggregationTemporality.DELTA,
            Histogram: AggregationTemporality.DELTA,
        }
        inner = _FakeInnerExporter(temporality)
        wrapper = _CircuitBreakerExporter(inner, logger)
        reader = PeriodicExportingMetricReader(
            wrapper, export_interval_millis=math.inf
        )
        try:
            assert reader._preferred_temporality == temporality
        finally:
            reader.shutdown()

    def test_export_forwards_timeout_and_kwargs(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.append(MetricExportResult.SUCCESS)
        wrapper = _CircuitBreakerExporter(inner, logger)
        metrics_data = MagicMock()
        wrapper.export(metrics_data, timeout_millis=1234, extra_kwarg="sentinel")
        assert inner.export_calls == [(metrics_data, 1234, {"extra_kwarg": "sentinel"})]

    def test_force_flush_forwards_timeout_before_trip(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        wrapper = _CircuitBreakerExporter(inner, logger)
        assert wrapper.force_flush(timeout_millis=5000) is True
        assert inner.force_flush_calls == [5000]

    def test_force_flush_is_noop_after_trip(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.extend([MetricExportResult.FAILURE] * 3)
        wrapper = _CircuitBreakerExporter(inner, logger)
        for _ in range(3):
            wrapper.export(MagicMock())
        assert wrapper.force_flush(timeout_millis=5000) is True
        assert inner.force_flush_calls == []

    def test_shutdown_forwards_timeout_millis_and_kwargs(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        wrapper = _CircuitBreakerExporter(inner, logger)
        wrapper.shutdown(timeout_millis=9999, extra_kwarg="sentinel")
        assert inner.shutdown_calls == [(9999, {"extra_kwarg": "sentinel"})]

    def test_shutdown_accepts_timeout_kwarg_from_real_reader(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        wrapper = _CircuitBreakerExporter(inner, logger)
        wrapper.shutdown(timeout=1.5)
        assert inner.shutdown_calls == [(30_000, {"timeout": 1.5})]

    def test_shutdown_delegates_exactly_once_including_after_trip(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.extend([MetricExportResult.FAILURE] * 3)
        wrapper = _CircuitBreakerExporter(inner, logger)
        for _ in range(3):
            wrapper.export(MagicMock())
        wrapper.shutdown()
        wrapper.shutdown()
        assert len(inner.shutdown_calls) == 1

    def test_export_returns_failure_and_increments_state_on_failure_result(
        self, logger
    ):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.append(MetricExportResult.FAILURE)
        wrapper = _CircuitBreakerExporter(inner, logger)
        result = wrapper.export(MagicMock())
        assert result == MetricExportResult.FAILURE
        assert wrapper._consecutive_failures == 1
        logger.info.assert_not_called()

    def test_export_catches_exception_logs_and_returns_failure(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.append(RuntimeError("boom"))
        wrapper = _CircuitBreakerExporter(inner, logger)
        result = wrapper.export(MagicMock())
        assert result == MetricExportResult.FAILURE
        assert wrapper._consecutive_failures == 1
        logger.info.assert_called_once()

    def test_export_resets_failure_count_after_success(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.extend(
            [MetricExportResult.FAILURE, MetricExportResult.SUCCESS]
        )
        wrapper = _CircuitBreakerExporter(inner, logger)
        wrapper.export(MagicMock())
        assert wrapper._consecutive_failures == 1
        wrapper.export(MagicMock())
        assert wrapper._consecutive_failures == 0

    @pytest.mark.parametrize(
        "outcomes",
        [
            [MetricExportResult.FAILURE] * 3,
            [RuntimeError("boom")] * 3,
            [MetricExportResult.FAILURE, RuntimeError("boom"), MetricExportResult.FAILURE],
        ],
    )
    def test_export_trips_on_third_consecutive_failure(self, logger, outcomes):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.extend(outcomes)
        wrapper = _CircuitBreakerExporter(inner, logger)
        for _ in range(3):
            wrapper.export(MagicMock())
        assert wrapper._tripped is True

    def test_export_third_attempt_returns_actual_failure_not_synthetic_success(
        self, logger
    ):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.extend([MetricExportResult.FAILURE] * 3)
        wrapper = _CircuitBreakerExporter(inner, logger)
        results = [wrapper.export(MagicMock()) for _ in range(3)]
        assert results == [MetricExportResult.FAILURE] * 3

    def test_export_after_trip_never_calls_inner_and_no_further_logs(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.extend([MetricExportResult.FAILURE] * 3)
        wrapper = _CircuitBreakerExporter(inner, logger)
        for _ in range(3):
            wrapper.export(MagicMock())
        logger.reset_mock()
        result = wrapper.export(MagicMock())
        assert result == MetricExportResult.SUCCESS
        assert len(inner.export_calls) == 3
        logger.info.assert_not_called()

    def test_three_consecutive_exceptions_emit_three_info_plus_one_trip_log(
        self, logger
    ):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.extend([RuntimeError("boom")] * 3)
        wrapper = _CircuitBreakerExporter(inner, logger)
        for _ in range(3):
            wrapper.export(MagicMock())
        assert logger.info.call_count == 4
        assert "3 consecutive failures" in logger.info.call_args_list[-1].args[0]

    def test_export_and_shutdown_are_mutually_exclusive(self, logger):
        from solnlib.observability import _CircuitBreakerExporter

        inner = _FakeInnerExporter()
        inner.results.append(MetricExportResult.SUCCESS)
        export_started = threading.Event()
        release_export = threading.Event()
        real_export = inner.export

        def blocking_export(metrics_data, timeout_millis=10_000, **kwargs):
            export_started.set()
            release_export.wait(timeout=5)
            return real_export(metrics_data, timeout_millis=timeout_millis, **kwargs)

        inner.export = blocking_export
        wrapper = _CircuitBreakerExporter(inner, logger)

        export_thread = threading.Thread(target=wrapper.export, args=(MagicMock(),))
        export_thread.start()
        assert export_started.wait(timeout=5)

        shutdown_thread = threading.Thread(target=wrapper.shutdown)
        shutdown_thread.start()
        time.sleep(0.2)
        assert wrapper._shutdown_called is False
        assert inner.shutdown_calls == []

        release_export.set()
        export_thread.join(timeout=5)
        shutdown_thread.join(timeout=5)

        assert wrapper._shutdown_called is True
        assert len(inner.shutdown_calls) == 1


# ---------------------------------------------------------------------------
# ObservabilityService
# ---------------------------------------------------------------------------


def _make_service(logger, monkeypatch, extra_exporters=None):
    """Create an ObservabilityService with OTLP disabled and app.conf
    mocked."""
    monkeypatch.setattr(
        "solnlib.observability.ObservabilityService._create_otlp_exporter",
        lambda self: None,
    )
    return ObservabilityService(
        modinput_type="test-input",
        logger=logger,
        ta_name="my_ta",
        ta_version="1.0.0",
        extra_exporters=extra_exporters,
    )


class TestObservabilityService:
    def test_counters_are_created(self, logger, monkeypatch):
        # Arrange / Act
        svc = _make_service(logger, monkeypatch)
        # Assert
        assert svc.event_count_counter is not None
        assert svc.event_bytes_counter is not None

    def test_meter_is_available(self, logger, monkeypatch):
        # Arrange / Act
        svc = _make_service(logger, monkeypatch)
        # Assert
        assert svc._meter is not None

    def test_extra_exporter_is_added(self, logger, monkeypatch):
        # Arrange
        extra = MagicMock()
        # Act / Assert
        _make_service(logger, monkeypatch, extra_exporters=[extra])
        # No assertion needed beyond not raising; the exporter is wrapped internally

    def test_missing_ta_name_logs_info(self, logger, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._read_ta_info",
            lambda self: (None, None),
        )
        # Act
        svc = ObservabilityService(modinput_type="test-input", logger=logger)
        # Assert
        assert svc._meter is None
        logger.info.assert_called()
        logger.warning.assert_not_called()

    def test_register_instrument_returns_none_when_meter_missing(
        self, logger, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._read_ta_info",
            lambda self: (None, None),
        )
        svc = ObservabilityService(modinput_type="test-input", logger=logger)
        # Act
        result = svc.register_instrument(lambda m: m.create_counter("x"))
        # Assert
        assert result is None

    def test_register_instrument_calls_callback(self, logger, monkeypatch):
        # Arrange
        svc = _make_service(logger, monkeypatch)
        callback = MagicMock(return_value="instrument")
        # Act
        result = svc.register_instrument(callback)
        # Assert
        callback.assert_called_once_with(svc._meter)
        assert result == "instrument"

    def test_read_ta_info_returns_values(self, logger, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.get_conf_stanzas",
            lambda conf, **kwargs: {
                "id": {"name": "my_ta"},
                "launcher": {"version": "2.0.0"},
            },
        )
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        # Act
        svc = ObservabilityService(modinput_type="test-input", logger=logger)
        # Assert
        assert svc._meter is not None

    def test_read_ta_info_handles_exception(self, logger, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        monkeypatch.setattr(
            "solnlib.observability.get_conf_stanzas",
            MagicMock(side_effect=Exception("no btool")),
        )
        # Act
        svc = ObservabilityService(modinput_type="test-input", logger=logger)
        # Assert
        assert svc._meter is None

    def test_resolve_otlp_port_from_env(self, logger, monkeypatch):
        # Arrange
        monkeypatch.setenv("SPOTLIGHT_OTEL_RECEIVER_PORT", "4317")
        svc = _make_service(logger, monkeypatch)
        # Act / Assert
        assert svc._resolve_otlp_port() == "4317"

    def test_resolve_otlp_port_falls_back_to_ipc(self, logger, monkeypatch):
        # Arrange
        monkeypatch.delenv("SPOTLIGHT_OTEL_RECEIVER_PORT", raising=False)
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._discover_otlp_port_via_ipc_broker",
            lambda self: "9999",
        )
        svc = _make_service(logger, monkeypatch)
        # Act / Assert
        assert svc._resolve_otlp_port() == "9999"

    def test_get_ipc_broker_port_returns_none_on_error(self, logger, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.get_conf_stanzas",
            MagicMock(side_effect=Exception("fail")),
        )
        svc = _make_service(logger, monkeypatch)
        # Act / Assert
        assert svc._get_ipc_broker_port() is None

    def test_get_ipc_broker_port_returns_port(self, logger, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.get_conf_stanzas",
            lambda conf, **kwargs: {"ipc_broker": {"port": "8088"}},
        )
        svc = _make_service(logger, monkeypatch)
        # Act / Assert
        assert svc._get_ipc_broker_port() == 8088

    def test_discover_otlp_port_returns_none_when_ipc_port_missing(
        self, logger, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._get_ipc_broker_port",
            lambda self: None,
        )
        svc = _make_service(logger, monkeypatch)
        # Act / Assert
        assert svc._discover_otlp_port_via_ipc_broker() is None

    def test_discover_otlp_port_returns_none_on_http_error(self, logger, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._get_ipc_broker_port",
            lambda self: 8088,
        )
        monkeypatch.setattr(
            "urllib.request.urlopen",
            MagicMock(side_effect=Exception("connection refused")),
        )
        svc = _make_service(logger, monkeypatch)
        # Act / Assert
        assert svc._discover_otlp_port_via_ipc_broker() is None

    def test_discover_otlp_port_returns_none_on_unsuccessful_response(
        self, logger, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._get_ipc_broker_port",
            lambda self: 8088,
        )
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b'{"success": false}'
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: mock_resp)
        svc = _make_service(logger, monkeypatch)
        # Act / Assert
        assert svc._discover_otlp_port_via_ipc_broker() is None

    def test_discover_otlp_port_returns_port_on_success(self, logger, monkeypatch):
        # Arrange
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._get_ipc_broker_port",
            lambda self: 8088,
        )
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b'{"success": true, "port": 4317}'
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: mock_resp)
        svc = _make_service(logger, monkeypatch)
        # Act / Assert
        assert svc._discover_otlp_port_via_ipc_broker() == "4317"

    def test_create_otlp_exporter_returns_none_when_no_port(self, logger, monkeypatch):
        # Arrange
        monkeypatch.delenv("SPOTLIGHT_OTEL_RECEIVER_PORT", raising=False)
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._discover_otlp_port_via_ipc_broker",
            lambda self: None,
        )
        svc = _make_service(logger, monkeypatch)
        # Act — call the real _create_otlp_exporter (not patched)
        result = ObservabilityService._create_otlp_exporter(svc)
        # Assert
        assert result is None

    def test_create_otlp_exporter_returns_none_when_cert_missing(
        self, logger, monkeypatch, tmp_path
    ):
        # Arrange
        monkeypatch.setenv("SPOTLIGHT_OTEL_RECEIVER_PORT", "4317")
        monkeypatch.setenv("SPLUNK_HOME", str(tmp_path))
        svc = _make_service(logger, monkeypatch)
        # Act
        result = ObservabilityService._create_otlp_exporter(svc)
        # Assert
        assert result is None

    def test_create_otlp_exporter_returns_exporter_when_cert_present(
        self, logger, monkeypatch, tmp_path
    ):
        # Arrange
        monkeypatch.setenv("SPOTLIGHT_OTEL_RECEIVER_PORT", "4317")
        monkeypatch.setenv("SPLUNK_HOME", str(tmp_path))
        cert_path = tmp_path / "var/packages/data/spotlight-collector"
        cert_path.mkdir(parents=True)
        (cert_path / "server.crt").write_bytes(b"fake-cert")
        # Patch grpc module directly (it's imported inside _create_otlp_exporter)
        mock_grpc = MagicMock()
        mock_grpc.ssl_channel_credentials = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(sys.modules, "grpc", mock_grpc)
        # Patch OTLPMetricExporter module
        mock_otlp_module = MagicMock()
        mock_exporter = MagicMock()
        mock_otlp_module.OTLPMetricExporter = MagicMock(return_value=mock_exporter)
        monkeypatch.setitem(
            sys.modules,
            "opentelemetry.exporter.otlp.proto.grpc.metric_exporter",
            mock_otlp_module,
        )
        # Build svc without patching _create_otlp_exporter so the real method is called
        svc = ObservabilityService(
            modinput_type="test-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
        )
        # Act
        result = ObservabilityService._create_otlp_exporter(svc)
        # Assert
        assert result is mock_exporter

    def test_create_otlp_exporter_uses_delta_temporality(
        self, logger, monkeypatch, tmp_path
    ):
        # Arrange
        monkeypatch.setenv("SPOTLIGHT_OTEL_RECEIVER_PORT", "4317")
        monkeypatch.setenv("SPLUNK_HOME", str(tmp_path))
        cert_path = tmp_path / "var/packages/data/spotlight-collector"
        cert_path.mkdir(parents=True)
        (cert_path / "server.crt").write_bytes(b"fake-cert")
        # Patch grpc module directly (it's imported inside _create_otlp_exporter)
        mock_grpc = MagicMock()
        mock_grpc.ssl_channel_credentials = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(sys.modules, "grpc", mock_grpc)
        # Patch OTLPMetricExporter module
        mock_exporter_cls = MagicMock(return_value=MagicMock())
        mock_otlp_module = MagicMock()
        mock_otlp_module.OTLPMetricExporter = mock_exporter_cls
        monkeypatch.setitem(
            sys.modules,
            "opentelemetry.exporter.otlp.proto.grpc.metric_exporter",
            mock_otlp_module,
        )
        # Do NOT use _make_service — it patches _create_otlp_exporter away.
        # Create a bare svc object and call the real method directly.
        svc = ObservabilityService(
            modinput_type="test-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
        )
        mock_exporter_cls.reset_mock()
        # Act
        ObservabilityService._create_otlp_exporter(svc)
        # Assert — preferred_temporality must set DELTA for Counter and Histogram
        _, kwargs = mock_exporter_cls.call_args
        temporality = kwargs["preferred_temporality"]
        assert temporality[Counter] == AggregationTemporality.DELTA
        assert temporality[Histogram] == AggregationTemporality.DELTA

    def test_flush_calls_provider_force_flush(self, logger, monkeypatch):
        # Arrange
        svc = _make_service(logger, monkeypatch)
        mock_provider = MagicMock()
        svc._provider = mock_provider
        # Act
        svc.flush(timeout_millis=5_000)
        # Assert
        mock_provider.force_flush.assert_called_once_with(timeout_millis=5000)

    def test_flush_is_noop_when_provider_missing(self, logger, monkeypatch):
        # Arrange
        svc = _make_service(logger, monkeypatch)
        svc._provider = None
        # Act / Assert — must not raise
        svc.flush()

    def test_flush_logs_info_on_exception(self, logger, monkeypatch):
        # Arrange
        svc = _make_service(logger, monkeypatch)
        mock_provider = MagicMock()
        mock_provider.force_flush.side_effect = RuntimeError("boom")
        svc._provider = mock_provider
        # Act
        svc.flush()
        # Assert
        logger.info.assert_called()
        logger.warning.assert_not_called()

    def test_init_attaches_filter_to_metrics_sdk_loggers(self, logger, monkeypatch):
        from solnlib.observability import (
            _downgrade_to_info_filter,
            _METRICS_SDK_LOGGERS,
        )

        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        with _clean_logger_filters(*_METRICS_SDK_LOGGERS) as loggers:
            ObservabilityService(
                modinput_type="test-input",
                logger=logger,
                ta_name="my_ta",
                ta_version="1.0.0",
            )
            for lg in loggers:
                assert _downgrade_to_info_filter in lg.filters

    def test_init_does_not_attach_filter_to_unrelated_logger(self, logger, monkeypatch):
        from solnlib.observability import _downgrade_to_info_filter

        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        ObservabilityService(
            modinput_type="test-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
        )
        unrelated = logging.getLogger("opentelemetry.sdk.resources")
        assert _downgrade_to_info_filter not in unrelated.filters

    def test_module_importable_without_grpc(self, monkeypatch):
        # Arrange
        import builtins

        # Simulate grpc not being installed by temporarily hiding it
        grpc_mod = sys.modules.pop("grpc", None)
        otlp_mod = sys.modules.pop(
            "opentelemetry.exporter.otlp.proto.grpc.metric_exporter", None
        )
        # Also clear the observability module and any submodules
        obs_mods_to_clear = [
            k for k in sys.modules.keys() if k.startswith("solnlib.observability")
        ]
        saved_obs_mods = {k: sys.modules.pop(k) for k in obs_mods_to_clear}

        # Mock ImportError for grpc modules before import
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if (
                name == "grpc"
                or name == "opentelemetry.exporter.otlp.proto.grpc.metric_exporter"
            ):
                raise ModuleNotFoundError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        try:
            # Patch __import__ to raise for grpc modules
            builtins.__import__ = mock_import
            # Act
            import solnlib.observability as reimported_obs

            # Assert
            assert hasattr(reimported_obs, "ObservabilityService")
            assert hasattr(reimported_obs, "LoggerMetricExporter")
        except ImportError as e:
            pytest.fail(
                f"solnlib.observability should be importable without grpcio, but got: {e}"
            )
        finally:
            builtins.__import__ = original_import
            if grpc_mod is not None:
                sys.modules["grpc"] = grpc_mod
            if otlp_mod is not None:
                sys.modules[
                    "opentelemetry.exporter.otlp.proto.grpc.metric_exporter"
                ] = otlp_mod
            for k, v in saved_obs_mods.items():
                sys.modules[k] = v
            # `import solnlib.observability` also rebinds the `observability`
            # attribute on the `solnlib` package module; pytest's monkeypatch
            # dotted-path resolver reads that attribute in preference to
            # sys.modules, so it must be restored too or later
            # monkeypatch.setattr("solnlib.observability....") calls in the
            # same test run silently patch the discarded reimported module.
            if "solnlib.observability" in saved_obs_mods:
                import solnlib

                solnlib.observability = saved_obs_mods["solnlib.observability"]

    def test_create_otlp_exporter_sets_grpc_verbosity_when_absent(
        self, logger, monkeypatch
    ):
        monkeypatch.delenv("GRPC_VERBOSITY", raising=False)
        monkeypatch.delenv("SPOTLIGHT_OTEL_RECEIVER_PORT", raising=False)
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._discover_otlp_port_via_ipc_broker",
            lambda self: None,
        )
        svc = ObservabilityService(
            modinput_type="test-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
        )
        ObservabilityService._create_otlp_exporter(svc)
        assert os.environ["GRPC_VERBOSITY"] == "NONE"

    def test_create_otlp_exporter_respects_existing_grpc_verbosity(
        self, logger, monkeypatch
    ):
        monkeypatch.setenv("GRPC_VERBOSITY", "DEBUG")
        monkeypatch.delenv("SPOTLIGHT_OTEL_RECEIVER_PORT", raising=False)
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._discover_otlp_port_via_ipc_broker",
            lambda self: None,
        )
        svc = ObservabilityService(
            modinput_type="test-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
        )
        ObservabilityService._create_otlp_exporter(svc)
        assert os.environ["GRPC_VERBOSITY"] == "DEBUG"

    def test_create_otlp_exporter_attaches_filter_to_otlp_loggers(
        self, logger, monkeypatch, tmp_path
    ):
        from solnlib.observability import _downgrade_to_info_filter, _OTLP_LOGGERS

        monkeypatch.setenv("SPOTLIGHT_OTEL_RECEIVER_PORT", "4317")
        monkeypatch.setenv("SPLUNK_HOME", str(tmp_path))
        cert_path = tmp_path / "var/packages/data/spotlight-collector"
        cert_path.mkdir(parents=True)
        (cert_path / "server.crt").write_bytes(b"fake-cert")
        mock_grpc = MagicMock()
        mock_grpc.ssl_channel_credentials = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(sys.modules, "grpc", mock_grpc)
        mock_otlp_module = MagicMock()
        mock_otlp_module.OTLPMetricExporter = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(
            sys.modules,
            "opentelemetry.exporter.otlp.proto.grpc.metric_exporter",
            mock_otlp_module,
        )
        svc = ObservabilityService(
            modinput_type="test-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
        )
        with _clean_logger_filters(*_OTLP_LOGGERS) as loggers:
            ObservabilityService._create_otlp_exporter(svc)
            for lg in loggers:
                assert _downgrade_to_info_filter in lg.filters

    def test_create_otlp_exporter_does_not_attach_filter_on_missing_port(
        self, logger, monkeypatch
    ):
        from solnlib.observability import _downgrade_to_info_filter, _OTLP_LOGGERS

        monkeypatch.delenv("SPOTLIGHT_OTEL_RECEIVER_PORT", raising=False)
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._discover_otlp_port_via_ipc_broker",
            lambda self: None,
        )
        svc = _make_service(logger, monkeypatch)
        with _clean_logger_filters(*_OTLP_LOGGERS) as loggers:
            assert ObservabilityService._create_otlp_exporter(svc) is None
            for lg in loggers:
                assert _downgrade_to_info_filter not in lg.filters

    def test_filters_are_attached_before_construction_logs_occur(
        self, logger, monkeypatch, tmp_path
    ):
        """Regression guard for the required ordering: the filter must be on
        the logger *before* OTLPMetricExporter() runs, not merely present by
        the time _create_otlp_exporter() returns. Checking `.filters` after
        the call (as the two tests above do) cannot tell "attached early"
        apart from "attached late" — both leave the filter present at the
        end. This test instead attaches a capturing Handler to each OTLP
        logger *before* calling _create_otlp_exporter(), forces two of the
        four loggers to actually emit a WARNING during real OTLPMetricExporter
        construction (malformed OTEL_EXPORTER_OTLP_METRICS_HEADERS and
        OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE — verified against
        opentelemetry-exporter-otlp-proto-grpc 1.39.1 to log through
        `opentelemetry.util.re` and
        `opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder`
        respectively), and asserts every record the handler observed was
        already at INFO by the time it reached the handler. Filters run
        before handlers in Logger.handle(), so this only passes if the
        filter was attached before that specific log call — i.e. before
        OTLPMetricExporter() ran. Uses the real grpc/OTLPMetricExporter
        (no sys.modules mocking): constructing ssl_channel_credentials and
        OTLPMetricExporter does not perform network I/O, so no real
        collector is needed, and a syntactically-invalid cert file is
        accepted at construction time (verified empirically).

        Calls _create_otlp_exporter() on a bare instance built via
        ObservabilityService.__new__() rather than going through the full
        constructor. The full constructor would wrap the real returned
        exporter in a real PeriodicExportingMetricReader — in OTel 1.39.1
        that reader defaults export_interval_millis to 60_000 and spawns a
        genuine daemon thread (MeterProvider also registers an atexit
        shutdown hook), and nothing in this test would ever join or shut
        that thread down. _create_otlp_exporter only reads self._logger
        (SPOTLIGHT_OTEL_RECEIVER_PORT is set below, so _resolve_otlp_port()
        never touches the IPC-broker path, which is the only other place
        that reads self attributes), so a bare instance with just _logger
        set is sufficient. The real exporter this returns still opens a
        gRPC channel object, so it is explicitly shut down in finally."""
        from solnlib.observability import _OTLP_LOGGERS

        monkeypatch.setenv("SPOTLIGHT_OTEL_RECEIVER_PORT", "4317")
        monkeypatch.setenv("SPLUNK_HOME", str(tmp_path))
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_METRICS_HEADERS", "not-a-valid-header-no-equals-sign"
        )
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE",
            "not-a-real-preference",
        )
        cert_path = tmp_path / "var/packages/data/spotlight-collector"
        cert_path.mkdir(parents=True)
        (cert_path / "server.crt").write_bytes(b"fake-cert")

        svc = ObservabilityService.__new__(ObservabilityService)
        svc._logger = logger

        captured = []  # list of (logger_name, levelno) tuples

        class _CapturingHandler(logging.Handler):
            def emit(self, record):
                captured.append((record.name, record.levelno))

        capturing_handler = _CapturingHandler(level=logging.NOTSET)

        with _clean_logger_filters(*_OTLP_LOGGERS) as loggers:
            original_levels = [lg.level for lg in loggers]
            for lg in loggers:
                lg.addHandler(capturing_handler)
                lg.setLevel(logging.NOTSET)
            exporter = None
            try:
                exporter = svc._create_otlp_exporter()
            finally:
                for lg, level in zip(loggers, original_levels):
                    lg.removeHandler(capturing_handler)
                    lg.setLevel(level)
                if exporter is not None:
                    exporter.shutdown()

        captured_logger_names = {name for name, _ in captured}
        assert "opentelemetry.util.re" in captured_logger_names, (
            "expected the malformed-headers trigger to still log through "
            "opentelemetry.util.re — if this fails, the trigger stopped "
            "working and the test no longer proves anything"
        )
        assert (
            "opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder"
            in captured_logger_names
        ), (
            "expected the malformed-temporality-preference trigger to still "
            "log through the metrics encoder — if this fails, the trigger "
            "stopped working and the test no longer proves anything"
        )
        assert all(levelno <= logging.INFO for _, levelno in captured)


# ---------------------------------------------------------------------------
# _DowngradeToInfoFilter
# ---------------------------------------------------------------------------


class TestDowngradeToInfoFilter:
    def test_downgrades_error_and_critical_to_info(self):
        from solnlib.observability import _downgrade_to_info_filter

        for level in (logging.ERROR, logging.CRITICAL):
            record = logging.LogRecord(
                "x", level, __file__, 1, "msg %s", ("arg",), None
            )
            assert _downgrade_to_info_filter.filter(record) is True
            assert record.levelno == logging.INFO
            assert record.levelname == "INFO"
            assert record.msg == "msg %s"
            assert record.args == ("arg",)

    def test_preserves_debug_and_info(self):
        from solnlib.observability import _downgrade_to_info_filter

        for level in (logging.DEBUG, logging.INFO):
            record = logging.LogRecord(
                "x", level, __file__, 1, "msg %s", ("arg",), None
            )
            _downgrade_to_info_filter.filter(record)
            assert record.levelno == level
            assert record.msg == "msg %s"
            assert record.args == ("arg",)

    def test_repeated_attachment_does_not_duplicate(self):
        from solnlib.observability import _downgrade_to_info_filter

        test_logger = logging.getLogger("test.solnlib.observability.dedup")
        test_logger.filters = []
        test_logger.addFilter(_downgrade_to_info_filter)
        test_logger.addFilter(_downgrade_to_info_filter)
        assert test_logger.filters.count(_downgrade_to_info_filter) == 1
        test_logger.filters = []

    def test_otlp_and_metrics_sdk_logger_names_are_defined(self):
        from solnlib.observability import _METRICS_SDK_LOGGERS, _OTLP_LOGGERS

        assert _OTLP_LOGGERS == (
            "opentelemetry.exporter.otlp.proto.grpc.exporter",
            "opentelemetry.util.re",
            "opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder",
            "opentelemetry.exporter.otlp.proto.common._internal",
        )
        assert _METRICS_SDK_LOGGERS == (
            "opentelemetry.sdk.metrics._internal.export",
            "opentelemetry.sdk.metrics._internal",
            "opentelemetry.sdk.metrics._internal.instrument",
            "opentelemetry.metrics._internal",
            "opentelemetry.attributes",
        )


# ---------------------------------------------------------------------------
# Log-level downgrade (WARNING/ERROR -> INFO)
# ---------------------------------------------------------------------------


class TestLogLevelDowngrade:
    def test_logger_metric_exporter_export_exception_uses_safe_str(
        self, logger, monkeypatch
    ):
        monkeypatch.setattr(
            "solnlib.observability._safe_exception_str", lambda error: "SAFE"
        )
        metrics_data = MagicMock()
        metrics_data.resource_metrics.__iter__ = MagicMock(
            side_effect=RuntimeError("boom")
        )
        exporter = LoggerMetricExporter(logger)
        exporter.export(metrics_data)
        logger.info.assert_called_once()
        args, kwargs = logger.info.call_args
        assert "SAFE" in args
        assert "exc_info" not in kwargs

    def test_init_exception_uses_safe_str(self, logger, monkeypatch):
        monkeypatch.setattr(
            "solnlib.observability._safe_exception_str", lambda error: "SAFE"
        )
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._read_ta_info",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        ObservabilityService(modinput_type="test-input", logger=logger)
        assert any("SAFE" in call.args for call in logger.info.call_args_list)
        logger.warning.assert_not_called()

    def test_read_ta_info_exception_uses_safe_str(self, logger, monkeypatch):
        monkeypatch.setattr(
            "solnlib.observability._safe_exception_str", lambda error: "SAFE"
        )
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        monkeypatch.setattr(
            "solnlib.observability.get_conf_stanzas",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        svc = ObservabilityService(modinput_type="test-input", logger=logger)
        assert svc._meter is None
        assert any("SAFE" in call.args for call in logger.info.call_args_list)
        logger.warning.assert_not_called()

    def test_get_ipc_broker_port_exception_uses_safe_str(self, logger, monkeypatch):
        monkeypatch.setattr(
            "solnlib.observability._safe_exception_str", lambda error: "SAFE"
        )
        monkeypatch.setattr(
            "solnlib.observability.get_conf_stanzas",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        svc = _make_service(logger, monkeypatch)
        logger.reset_mock()
        assert svc._get_ipc_broker_port() is None
        assert any("SAFE" in call.args for call in logger.info.call_args_list)
        logger.warning.assert_not_called()

    def test_discover_otlp_port_missing_broker_port_is_info(self, logger, monkeypatch):
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._get_ipc_broker_port",
            lambda self: None,
        )
        svc = _make_service(logger, monkeypatch)
        logger.reset_mock()
        assert svc._discover_otlp_port_via_ipc_broker() is None
        logger.info.assert_called()
        logger.warning.assert_not_called()

    def test_discover_otlp_port_unsuccessful_response_is_info(
        self, logger, monkeypatch
    ):
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._get_ipc_broker_port",
            lambda self: 8088,
        )
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b'{"success": false}'
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: mock_resp)
        svc = _make_service(logger, monkeypatch)
        logger.reset_mock()
        assert svc._discover_otlp_port_via_ipc_broker() is None
        logger.info.assert_called()
        logger.warning.assert_not_called()

    def test_discover_otlp_port_exception_uses_safe_str(self, logger, monkeypatch):
        monkeypatch.setattr(
            "solnlib.observability._safe_exception_str", lambda error: "SAFE"
        )
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._get_ipc_broker_port",
            lambda self: 8088,
        )
        monkeypatch.setattr(
            "urllib.request.urlopen",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        svc = _make_service(logger, monkeypatch)
        logger.reset_mock()
        assert svc._discover_otlp_port_via_ipc_broker() is None
        assert any("SAFE" in call.args for call in logger.info.call_args_list)
        logger.warning.assert_not_called()

    def test_create_otlp_exporter_missing_port_is_info(self, logger, monkeypatch):
        monkeypatch.delenv("SPOTLIGHT_OTEL_RECEIVER_PORT", raising=False)
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._discover_otlp_port_via_ipc_broker",
            lambda self: None,
        )
        # Create service WITHOUT patching _create_otlp_exporter
        svc = ObservabilityService(
            modinput_type="test-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
        )
        logger.reset_mock()
        assert ObservabilityService._create_otlp_exporter(svc) is None
        logger.info.assert_called()
        logger.warning.assert_not_called()

    def test_create_otlp_exporter_missing_cert_is_info(
        self, logger, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("SPOTLIGHT_OTEL_RECEIVER_PORT", "4317")
        monkeypatch.setenv("SPLUNK_HOME", str(tmp_path))
        # Create service WITHOUT patching _create_otlp_exporter
        svc = ObservabilityService(
            modinput_type="test-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
        )
        logger.reset_mock()
        assert ObservabilityService._create_otlp_exporter(svc) is None
        logger.info.assert_called()
        logger.error.assert_not_called()

    def test_create_otlp_exporter_exception_uses_safe_str_no_exc_info(
        self, logger, monkeypatch
    ):
        monkeypatch.setattr(
            "solnlib.observability._safe_exception_str", lambda error: "SAFE"
        )
        monkeypatch.setenv("SPOTLIGHT_OTEL_RECEIVER_PORT", "4317")
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._resolve_otlp_port",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        # Create service WITHOUT patching _create_otlp_exporter
        svc = ObservabilityService(
            modinput_type="test-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
        )
        logger.reset_mock()
        assert ObservabilityService._create_otlp_exporter(svc) is None
        logger.info.assert_called_once()
        args, kwargs = logger.info.call_args
        assert "SAFE" in args
        assert "exc_info" not in kwargs
        logger.warning.assert_not_called()

    def test_flush_exception_uses_safe_str(self, logger, monkeypatch):
        monkeypatch.setattr(
            "solnlib.observability._safe_exception_str", lambda error: "SAFE"
        )
        svc = _make_service(logger, monkeypatch)
        mock_provider = MagicMock()
        mock_provider.force_flush.side_effect = RuntimeError("boom")
        svc._provider = mock_provider
        logger.reset_mock()
        svc.flush()
        assert any("SAFE" in call.args for call in logger.info.call_args_list)
        logger.warning.assert_not_called()


# ---------------------------------------------------------------------------
# StanzaObservabilityRecorder
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=False)
def clear_stanza_recorder_cache():
    """Wipe the class-level singleton cache between tests."""
    from solnlib.observability import StanzaObservabilityRecorder

    StanzaObservabilityRecorder._instances.clear()
    yield
    StanzaObservabilityRecorder._instances.clear()


class TestStanzaObservabilityRecorder:
    def _make_recorder(self, monkeypatch, modinput_type="kql", stanza_name="my:stanza"):
        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        from solnlib.observability import StanzaObservabilityRecorder

        return StanzaObservabilityRecorder(
            modinput_type, MagicMock(spec=logging.Logger), stanza_name
        )

    def test_singleton_same_modinput_type_reuses_service(
        self, monkeypatch, clear_stanza_recorder_cache
    ):
        from solnlib.observability import StanzaObservabilityRecorder

        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        logger = MagicMock(spec=logging.Logger)
        r1 = StanzaObservabilityRecorder("kql", logger, "stanza-1")
        r2 = StanzaObservabilityRecorder("kql", logger, "stanza-2")
        assert (
            StanzaObservabilityRecorder._instances["kql"]
            is StanzaObservabilityRecorder._instances["kql"]
        )
        assert r1._service is r2._service

    def test_singleton_different_modinput_types_create_separate_services(
        self, monkeypatch, clear_stanza_recorder_cache
    ):
        from solnlib.observability import StanzaObservabilityRecorder

        monkeypatch.setattr(
            "solnlib.observability.ObservabilityService._create_otlp_exporter",
            lambda self: None,
        )
        logger = MagicMock(spec=logging.Logger)
        r1 = StanzaObservabilityRecorder("kql", logger, "stanza-1")
        r2 = StanzaObservabilityRecorder("event-hub", logger, "stanza-2")
        assert r1._service is not r2._service
        assert "kql" in StanzaObservabilityRecorder._instances
        assert "event-hub" in StanzaObservabilityRecorder._instances

    def test_record_calls_add_with_stanza_name(
        self, monkeypatch, clear_stanza_recorder_cache
    ):
        rec = self._make_recorder(monkeypatch)
        mock_count = MagicMock()
        mock_bytes = MagicMock()
        rec._service.event_count_counter = mock_count
        rec._service.event_bytes_counter = mock_bytes
        mock_count.reset_mock()
        mock_bytes.reset_mock()

        rec.record(5, 1024)

        mock_count.add.assert_called_once_with(
            5, attributes={"splunk.modinput.name": "my:stanza"}
        )
        mock_bytes.add.assert_called_once_with(
            1024, attributes={"splunk.modinput.name": "my:stanza"}
        )

    def test_record_merges_extra_attrs(self, monkeypatch, clear_stanza_recorder_cache):
        rec = self._make_recorder(monkeypatch)
        mock_count = MagicMock()
        mock_bytes = MagicMock()
        rec._service.event_count_counter = mock_count
        rec._service.event_bytes_counter = mock_bytes
        mock_count.reset_mock()
        mock_bytes.reset_mock()

        rec.record(3, 512, extra_attrs={"partition.id": "0"})

        mock_count.add.assert_called_once_with(
            3,
            attributes={"splunk.modinput.name": "my:stanza", "partition.id": "0"},
        )

    def test_record_noop_when_counters_none(
        self, monkeypatch, clear_stanza_recorder_cache
    ):
        rec = self._make_recorder(monkeypatch)
        rec._service.event_count_counter = None
        rec._service.event_bytes_counter = None
        # Must not raise
        rec.record(10, 2048)

    def test_emit_zero_baseline_called_in_init(self, clear_stanza_recorder_cache):
        from solnlib.observability import StanzaObservabilityRecorder

        logger = MagicMock(spec=logging.Logger)
        with patch.object(StanzaObservabilityRecorder, "record") as mock_record:
            StanzaObservabilityRecorder("kql", logger, "my-stanza")

        mock_record.assert_called_once_with(0, 0)

    def test_flush_delegates_to_service(self, monkeypatch, clear_stanza_recorder_cache):
        rec = self._make_recorder(monkeypatch)
        mock_service = MagicMock()
        rec._service = mock_service

        rec.flush()

        mock_service.flush.assert_called_once()

    def test_context_manager_calls_flush_on_exit(
        self, monkeypatch, clear_stanza_recorder_cache
    ):
        rec = self._make_recorder(monkeypatch)
        with patch.object(rec, "flush") as mock_flush:
            with rec:
                pass
            mock_flush.assert_called_once()

    def test_context_manager_does_not_suppress_exceptions(
        self, monkeypatch, clear_stanza_recorder_cache
    ):
        rec = self._make_recorder(monkeypatch)
        with pytest.raises(ValueError):
            with rec:
                raise ValueError("boom")

    def test_register_instrument_delegates_to_service(
        self, monkeypatch, clear_stanza_recorder_cache
    ):
        rec = self._make_recorder(monkeypatch)
        mock_service = MagicMock()
        mock_instrument = MagicMock()
        mock_service.register_instrument.return_value = mock_instrument
        rec._service = mock_service

        def callback(meter):
            return meter.create_counter("x")

        result = rec.register_instrument(callback)

        mock_service.register_instrument.assert_called_once_with(callback)
        assert result is mock_instrument

    def test_register_instrument_returns_none_when_service_not_initialised(
        self, monkeypatch, clear_stanza_recorder_cache
    ):
        rec = self._make_recorder(monkeypatch)
        mock_service = MagicMock()
        mock_service.register_instrument.return_value = None
        rec._service = mock_service

        result = rec.register_instrument(lambda meter: meter.create_counter("x"))

        assert result is None


class TestGrpcTlsHandshakeStderrSuppression:
    """Integration check: a real TLS handshake failure logs a gRPC C-core
    diagnostic line straight to stderr unless GRPC_VERBOSITY=NONE is set
    before grpc initializes. Requires the system `openssl` binary."""

    @staticmethod
    def _generate_self_signed_cert(directory, name, subject):
        key_path = directory / f"{name}.key"
        crt_path = directory / f"{name}.crt"
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(key_path),
                "-out",
                str(crt_path),
                "-days",
                "1",
                "-nodes",
                "-subj",
                subject,
            ],
            check=True,
            capture_output=True,
        )
        return key_path, crt_path

    @pytest.mark.skipif(
        shutil.which("openssl") is None, reason="requires system openssl binary"
    )
    def test_grpc_verbosity_none_suppresses_tls_handshake_stderr(self, tmp_path):
        server_key, server_crt = self._generate_self_signed_cert(
            tmp_path, "server", "/CN=localhost"
        )
        _, wrong_root_crt = self._generate_self_signed_cert(
            tmp_path, "wrong_root", "/CN=wrong-root"
        )

        control_env = dict(os.environ)
        control_env.pop("GRPC_VERBOSITY", None)
        control = subprocess.run(
            [
                sys.executable,
                "-c",
                _GRPC_TLS_HANDSHAKE_SCRIPT,
                str(server_key),
                str(server_crt),
                str(wrong_root_crt),
            ],
            env=control_env,
            capture_output=True,
            text=True,
            timeout=15,
        )

        suppressed_env = dict(os.environ)
        suppressed_env["GRPC_VERBOSITY"] = "NONE"
        suppressed = subprocess.run(
            [
                sys.executable,
                "-c",
                _GRPC_TLS_HANDSHAKE_SCRIPT,
                str(server_key),
                str(server_crt),
                str(wrong_root_crt),
            ],
            env=suppressed_env,
            capture_output=True,
            text=True,
            timeout=15,
        )

        assert "Handshake failed" in control.stderr
        assert "Handshake failed" not in suppressed.stderr
