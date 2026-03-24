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

import logging
from unittest.mock import MagicMock

import pytest
from opentelemetry.sdk.metrics.export import MetricExportResult

from solnlib.observability import LoggerMetricExporter, ObservabilityService


@pytest.fixture
def logger():
    return MagicMock(spec=logging.Logger)


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
        logger.error.assert_called()

    def test_shutdown_does_not_raise(self, logger):
        # Arrange / Act / Assert
        LoggerMetricExporter(logger).shutdown()

    def test_force_flush_returns_true(self, logger):
        # Arrange / Act / Assert
        assert LoggerMetricExporter(logger).force_flush() is True


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

    def test_missing_ta_name_logs_warning(self, logger, monkeypatch):
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
        logger.warning.assert_called()

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
