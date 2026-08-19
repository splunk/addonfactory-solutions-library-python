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
"""OpenTelemetry observability utilities for Splunk add-ons.

This module provides three public components:

- :class:`LoggerMetricExporter` — an OpenTelemetry ``MetricExporter`` that
  writes every exported data point to a standard Python logger.  It is useful
  for local development, debugging, and as a fallback when the Spotlight
  collector is not available.

- :class:`ObservabilityService` — a high-level wrapper that wires up a
  ``MeterProvider`` and creates the two mandatory event counters required by
  every Splunk add-on modular input.  It automatically tries to connect to the
  Splunk Spotlight OTLP collector and falls back silently when it is not
  reachable, so callers never have to handle observability failures themselves.

- :class:`StanzaObservabilityRecorder` — a stanza-scoped recorder that wraps
  ``ObservabilityService`` with a per-process singleton cache.  Bind it to a
  single stanza name and call :meth:`~StanzaObservabilityRecorder.record` after
  each batch of ingested events.  Use as a context manager for automatic flush
  on exit.

Typical usage::

    import logging
    from solnlib.observability import StanzaObservabilityRecorder

    logger = logging.getLogger(__name__)

    with StanzaObservabilityRecorder("my-input", logger, stanza_name) as obs:
        obs.record(len(events), total_bytes)
"""

import json
import logging
import os
import ssl
import threading
import urllib.request
from typing import Callable, ClassVar, Optional, Union
from .splunkenv import get_conf_stanzas
from opentelemetry.metrics import Instrument, Meter
from opentelemetry.sdk.metrics import MeterProvider, Counter, Histogram
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    MetricExporter,
    MetricExportResult,
    MetricsData,
    AggregationTemporality,
)
from opentelemetry.sdk.resources import Resource

_Logger = Union[logging.Logger, logging.LoggerAdapter]

_SPOTLIGHT_SIDECAR_NAME = "spotlight-collector"
_SPOTLIGHT_SERVICE_NAME = "spotlight_telemetry"
_SERVICE_NAMESPACE = "splunk.addon"

ATTR_MODINPUT_NAME = "splunk.modinput.name"


def _sanitize_for_log(text) -> str:
    """Return one bounded, UTF-8-safe physical log-line fragment."""
    try:
        # Calling the base implementation directly neutralizes overridden
        # methods on a str subclass and returns a genuine plain str.
        text = str.__str__(text) if isinstance(text, str) else str(text)
        text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        text = text.encode("utf-8", errors="replace").decode("utf-8")
        if len(text) > 500:
            text = text[:500] + "...(truncated)"
        return text
    except BaseException:
        return "<unrepresentable>"


def _safe_exception_repr(error: BaseException) -> str:
    try:
        return _sanitize_for_log(repr(error))
    except BaseException:
        pass
    try:
        return _sanitize_for_log(f"{type(error).__name__} (repr unavailable)")
    except BaseException:
        return "<exception repr unavailable>"


def _safe_exception_str(error: BaseException) -> str:
    try:
        return _sanitize_for_log(str(error))
    except BaseException:
        pass
    try:
        return _sanitize_for_log(f"{type(error).__name__} (details unavailable)")
    except BaseException:
        return "<exception details unavailable>"


class _DowngradeToInfoFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno > logging.INFO:
            record.levelno = logging.INFO
            record.levelname = "INFO"
        return True


_downgrade_to_info_filter = _DowngradeToInfoFilter()

_OTLP_LOGGERS = (
    "opentelemetry.exporter.otlp.proto.grpc.exporter",
    "opentelemetry.util.re",
    "opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder",
    "opentelemetry.exporter.otlp.proto.common._internal",
)

_METRICS_SDK_LOGGERS = (
    "opentelemetry.sdk.metrics._internal.export",
    "opentelemetry.sdk.metrics._internal",
    "opentelemetry.sdk.metrics._internal.instrument",
    "opentelemetry.metrics._internal",
    "opentelemetry.attributes",
)


class LoggerMetricExporter(MetricExporter):
    """An OpenTelemetry ``MetricExporter`` that logs every data point.

    Each exported data point is written to a standard Python logger at INFO
    level.  Counters are logged as ``value``, histograms as ``count``,
    ``sum``, ``min``, ``max``, ``bucket_counts``, and ``explicit_bounds``.

    This exporter is always available without any external infrastructure, so
    it is suitable for local development, CI environments, and as a fallback
    alongside the OTLP exporter.

    Both ``Counter`` and ``Histogram`` instruments use **delta** temporality,
    meaning each export interval reports only the change since the previous
    interval, not a cumulative total.

    Example::

        import logging
        from solnlib.observability import LoggerMetricExporter

        logger = logging.getLogger(__name__)
        exporter = LoggerMetricExporter(logger)

    Args:
        logger: The Python logger (or ``LoggerAdapter``) to write metrics to.
    """

    def __init__(self, logger: _Logger) -> None:
        super().__init__(
            preferred_temporality={
                Counter: AggregationTemporality.DELTA,
                Histogram: AggregationTemporality.DELTA,
            }
        )
        self._logger = logger

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        """Export metrics by writing each data point to the logger.

        Called automatically by the ``PeriodicExportingMetricReader`` on each
        export interval.  You do not need to call this method directly.

        Returns:
            ``MetricExportResult.SUCCESS`` on success, or
            ``MetricExportResult.FAILURE`` if an unexpected exception occurs.
        """
        try:
            metric_count = 0
            for resource_metrics in metrics_data.resource_metrics:
                for scope_metrics in resource_metrics.scope_metrics:
                    for metric in scope_metrics.metrics:
                        metric_count += 1
                        for data_point in metric.data.data_points:
                            attributes_dict = (
                                dict(data_point.attributes)
                                if data_point.attributes
                                else {}
                            )
                            if hasattr(data_point, "bucket_counts"):
                                self._logger.info(
                                    "OpenTelemetry Metric: %s  count=%s sum=%s "
                                    "min=%s max=%s bucket_counts=%s "
                                    "explicit_bounds=%s unit=%s %s",
                                    metric.name,
                                    data_point.count,
                                    data_point.sum,
                                    data_point.min,
                                    data_point.max,
                                    list(data_point.bucket_counts),
                                    list(data_point.explicit_bounds),
                                    metric.unit,
                                    attributes_dict,
                                )
                            else:
                                self._logger.info(
                                    "OpenTelemetry Metric: %s  value=%s unit=%s %s",
                                    metric.name,
                                    data_point.value,
                                    metric.unit,
                                    attributes_dict,
                                )

            if metric_count > 0:
                self._logger.debug(
                    "LoggerMetricExporter: Exported %d metric(s) successfully",
                    metric_count,
                )
            return MetricExportResult.SUCCESS
        except Exception as error:
            self._logger.info(
                "Failed to export metrics: %s", _safe_exception_str(error)
            )
            return MetricExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """No-op shutdown — the underlying logger needs no teardown."""

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Flush is a no-op for a synchronous logger; always returns
        ``True``."""
        return True


class _CircuitBreakerExporter(MetricExporter):
    """Wraps the internally constructed OTLP exporter and stops calling it
    after 3 consecutive failed exports in this process."""

    _MAX_CONSECUTIVE_FAILURES = 3

    def __init__(self, inner: MetricExporter, logger: _Logger) -> None:
        super().__init__(
            preferred_temporality=inner._preferred_temporality,
            preferred_aggregation=inner._preferred_aggregation,
        )
        self._inner = inner
        self._logger = logger
        self._consecutive_failures = 0
        self._tripped = False
        self._shutdown_called = False
        self._lock = threading.Lock()

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        with self._lock:
            if self._tripped:
                return MetricExportResult.SUCCESS

            try:
                result = self._inner.export(
                    metrics_data, timeout_millis=timeout_millis, **kwargs
                )
            except Exception as error:
                self._logger.info(
                    "OTLP export raised an exception: %s",
                    _safe_exception_repr(error),
                )
                result = MetricExportResult.FAILURE

            if result == MetricExportResult.SUCCESS:
                self._consecutive_failures = 0
                return result

            self._consecutive_failures += 1
            if self._consecutive_failures >= self._MAX_CONSECUTIVE_FAILURES:
                self._tripped = True
                self._logger.info("OTLP export disabled after 3 consecutive failures")
            return result

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        with self._lock:
            if self._tripped:
                return True
            return self._inner.force_flush(timeout_millis=timeout_millis)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        with self._lock:
            if self._shutdown_called:
                return
            self._shutdown_called = True
            self._inner.shutdown(timeout_millis=timeout_millis, **kwargs)


class ObservabilityService:
    """OpenTelemetry observability service for a Splunk modular input.

    Sets up a ``MeterProvider`` with two built-in event counters and,
    when the Spotlight collector is reachable, an OTLP gRPC exporter.
    Initialisation failures are caught and logged at INFO so that a
    missing or misconfigured observability stack never breaks the add-on.

    **Resource attributes** (fixed for the lifetime of the process):

    | Attribute                  | Value                  |
    |----------------------------|------------------------|
    | ``splunk.addon.name``      | *ta_name*              |
    | ``service.namespace``      | ``"splunk.addon"``     |
    | ``splunk.addon.version``   | *ta_version*           |
    | ``splunk.modinput.type``   | *modinput_type*        |

    **Built-in counters** (``None`` if initialisation failed):

    | Attribute               | Metric name                    | Unit  |
    |-------------------------|--------------------------------|-------|
    | ``event_count_counter`` | ``splunk.addon.events``        | ``1`` |
    | ``event_bytes_counter`` | ``splunk.addon.events.bytes``  | ``By``|

    Both counters accept ``ATTR_MODINPUT_NAME`` (``"splunk.modinput.name"``)
    as the only recommended data-point attribute.  Avoid adding other
    high-cardinality labels to these metrics.

    Additional instruments can be created with :meth:`register_instrument`.

    Example::

        import logging
        from solnlib.observability import (
            LoggerMetricExporter,
            ObservabilityService,
            ATTR_MODINPUT_NAME,
        )

        logger = logging.getLogger(__name__)

        obs = ObservabilityService(
            modinput_type="my-input",
            logger=logger,
            ta_name="my_ta",
            ta_version="1.0.0",
            extra_exporters=[LoggerMetricExporter(logger)],
        )

        # Record ingested events in your collection loop:
        attrs = {ATTR_MODINPUT_NAME: stanza_name}
        if obs.event_count_counter:
            obs.event_count_counter.add(len(events), attrs)
        if obs.event_bytes_counter:
            obs.event_bytes_counter.add(total_bytes, attrs)
    """

    def __init__(
        self,
        modinput_type: str,
        logger: _Logger,
        ta_name: Optional[str] = None,
        ta_version: Optional[str] = None,
        extra_exporters: Optional[list[MetricExporter]] = None,
    ):
        """Initialise the observability service.

        Args:
            modinput_type: Low-cardinality string identifying the modular input
                type, e.g. ``"event-hub"`` or ``"aws-s3"``.  Used as the
                ``splunk.modinput.type`` resource attribute.  Keep this value
                stable across restarts — it is a resource attribute, not a
                data-point label.
            logger: Python logger (or ``LoggerAdapter``) for all diagnostic
                output.  Typically the caller's own module-level logger.
            ta_name: Add-on identifier, e.g. ``"Splunk_TA_myapp"``.  When
                *None* the value is read from the ``[id]`` stanza of
                ``app.conf`` via :func:`~solnlib.splunkenv.get_conf_stanzas`.
                Pass it explicitly when the add-on runs outside a full Splunk
                environment or to avoid the ``app.conf`` lookup.
            ta_version: Add-on version string, e.g. ``"3.1.0"``.  When *None*
                the value is read from the ``[launcher]`` stanza of
                ``app.conf``.  Falls back to ``"unknown"`` if it cannot be
                determined.
            extra_exporters: Optional list of additional
                ``MetricExporter`` instances (e.g. :class:`LoggerMetricExporter`
                for local debug logging).  Each is wrapped in a
                ``PeriodicExportingMetricReader`` automatically, identical to
                how the OTLP exporter is handled.
        """
        self._logger: _Logger = logger
        self.event_count_counter: Optional[Counter] = None
        self.event_bytes_counter: Optional[Counter] = None
        self._meter: Optional[Meter] = None
        self._provider: Optional[MeterProvider] = None

        for logger_name in _METRICS_SDK_LOGGERS:
            logging.getLogger(logger_name).addFilter(_downgrade_to_info_filter)

        try:
            if type(modinput_type) is not str or not _is_safe_identifier_str(
                modinput_type
            ):
                raise ValueError(
                    "modinput_type must be a str without CR/LF, got "
                    f"{_sanitize_for_log(type(modinput_type).__name__)}"
                )

            if ta_name is None or ta_version is None:
                _ta_name, _ta_version = self._read_ta_info()
                ta_name = ta_name or _ta_name
                ta_version = ta_version or _ta_version or "unknown"

            if not ta_name:
                raise ValueError(
                    "ta_name could not be determined: pass it explicitly or ensure "
                    "app.conf is readable via btool"
                )

            resource = Resource(
                attributes={
                    "splunk.addon.name": ta_name,
                    "service.namespace": _SERVICE_NAMESPACE,
                    "splunk.addon.version": ta_version,
                    "splunk.modinput.type": modinput_type,
                }
            )

            metric_readers: list[PeriodicExportingMetricReader] = []
            otlp_exporter = self._create_otlp_exporter()
            if otlp_exporter:
                metric_readers.append(PeriodicExportingMetricReader(otlp_exporter))
                self._logger.info("OTLP gRPC exporter added to MeterProvider")
            for exporter in extra_exporters or []:
                metric_readers.append(PeriodicExportingMetricReader(exporter))

            self._provider = MeterProvider(
                resource=resource, metric_readers=metric_readers
            )
            self._meter = self._provider.get_meter(ta_name, ta_version)

            self.event_count_counter = self._meter.create_counter(
                name="splunk.addon.events",
                description="Number of events ingested by the add-on modular input",
                unit="1",
            )
            self.event_bytes_counter = self._meter.create_counter(
                name="splunk.addon.events.bytes",
                description="Volume of data ingested by the add-on modular input",
                unit="By",
            )

            self._logger.info(
                "ObservabilityService initialised: ta_name=%s ta_version=%s "
                "modinput_type=%s",
                ta_name,
                ta_version,
                modinput_type,
            )
        except Exception as error:
            self._logger.info(
                "Failed to initialise ObservabilityService: %s",
                _safe_exception_str(error),
            )

    def _read_ta_info(self) -> tuple[Optional[str], Optional[str]]:
        """Read the add-on name and version from ``app.conf``.

        Returns a ``(ta_name, ta_version)`` tuple.  Either value is
        ``None`` when the corresponding key is missing or when
        ``app.conf`` cannot be read (e.g. outside a Splunk environment).
        """
        try:
            stanzas = get_conf_stanzas("app")
            ta_name = stanzas.get("id", {}).get("name") or None
            scoped_stanzas = (
                get_conf_stanzas("app", app_name=ta_name) if ta_name else stanzas
            )
            ta_version = scoped_stanzas.get("launcher", {}).get("version") or None
            return ta_name, ta_version
        except Exception as error:
            self._logger.info(
                "Failed to read TA info from app.conf: %s",
                _safe_exception_str(error),
            )
            return None, None

    def _get_ipc_broker_port(self) -> Optional[int]:
        """Read the Spotlight IPC broker port from ``server.conf``.

        Returns the integer port number from the ``[ipc_broker]``
        stanza, or ``None`` if the stanza is absent or the file cannot
        be read.
        """
        try:
            stanzas = get_conf_stanzas("server")
            return int(stanzas["ipc_broker"]["port"])
        except Exception as error:
            self._logger.info(
                "Failed to read IPC broker port from server.conf: %s",
                _safe_exception_str(error),
            )
            return None

    def _discover_otlp_port_via_ipc_broker(self) -> Optional[str]:
        """Query the Spotlight IPC broker to discover the OTLP receiver port.

        Makes an HTTPS request to the local IPC broker's ``/v2/discover``
        endpoint (TLS verification disabled because the broker uses a
        self-signed certificate).  Returns the port as a string on success, or
        ``None`` if the broker is unreachable, returns an error, or reports
        ``"success": false``.
        """
        ipc_broker_port = self._get_ipc_broker_port()
        if ipc_broker_port is None:
            self._logger.info("IPC broker port not found in server.conf")
            return None

        url = (
            f"https://127.0.0.1:{ipc_broker_port}/v2/discover"
            f"?sidecarName={_SPOTLIGHT_SIDECAR_NAME}"
            f"&serviceName={_SPOTLIGHT_SERVICE_NAME}"
            f"&output_mode=json"
        )
        self._logger.info("Querying Spotlight IPC broker for OTLP port: %s", url)

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            if not data.get("success"):
                self._logger.info(
                    "IPC broker discovery returned unsuccessful response: %s", data
                )
                return None
            port = str(data["port"])
            self._logger.info("Discovered OTLP port via IPC broker: %s", port)
            return port
        except Exception as error:
            self._logger.info(
                "IPC broker OTLP port discovery failed: %s",
                _safe_exception_str(error),
            )
            return None

    def _resolve_otlp_port(self) -> Optional[str]:
        """Resolve the OTLP receiver port using a two-step lookup.

        1. Reads the ``SPOTLIGHT_OTEL_RECEIVER_PORT`` environment variable.
           Set this during development or testing to skip IPC broker discovery.
        2. Falls back to :meth:`_discover_otlp_port_via_ipc_broker`.

        Returns the port as a string, or ``None`` if neither source provides
        a value.
        """
        port = os.environ.get("SPOTLIGHT_OTEL_RECEIVER_PORT")
        if port:
            return port

        self._logger.info(
            "SPOTLIGHT_OTEL_RECEIVER_PORT not set, attempting IPC broker discovery"
        )
        return self._discover_otlp_port_via_ipc_broker()

    def _create_otlp_exporter(self) -> Optional[MetricExporter]:
        """Create a TLS-secured OTLP gRPC exporter targeting the Spotlight collector.

        ``grpc`` and ``OTLPMetricExporter`` are imported lazily inside this
        method so that ``import solnlib.observability`` succeeds in environments
        where ``grpcio`` is not installed.  The import only fails when OTLP
        export is actually attempted.

        The collector's server certificate is read from
        ``$SPLUNK_HOME/var/packages/data/spotlight-collector/server.crt``
        (defaults to ``/opt/splunk`` when ``SPLUNK_HOME`` is not set).

        Both ``Counter`` and ``Histogram`` instruments are configured with
        ``AggregationTemporality.DELTA`` so that each export interval reports
        only the change since the previous interval.

        Returns the configured exporter wrapped in ``_CircuitBreakerExporter``,
        or ``None`` when:

        - The OTLP port cannot be resolved (see :meth:`_resolve_otlp_port`).
        - The certificate file does not exist.
        - Any other exception occurs during exporter construction (including a
          missing ``grpcio`` package).
        """
        os.environ.setdefault("GRPC_VERBOSITY", "NONE")

        try:
            import grpc
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )

            splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
            otel_port = self._resolve_otlp_port()

            self._logger.info(
                "OTLP configuration: otel_port=%s, SPLUNK_HOME=%s",
                otel_port,
                splunk_home,
            )

            if not otel_port:
                self._logger.info(
                    "OTLP port could not be determined from env or IPC broker, "
                    "OTLP export disabled"
                )
                return None

            endpoint = f"localhost:{otel_port}"
            cert_file = os.path.join(
                splunk_home, "var/packages/data/spotlight-collector/server.crt"
            )
            self._logger.info(
                "Attempting to configure OTLP gRPC exporter for %s", endpoint
            )

            if not os.path.exists(cert_file):
                self._logger.info(
                    "OTel Collector certificate not found at %s, OTLP export disabled",
                    cert_file,
                )
                return None

            for logger_name in _OTLP_LOGGERS:
                logging.getLogger(logger_name).addFilter(_downgrade_to_info_filter)

            with open(cert_file, "rb") as f:
                server_cert = f.read()

            credentials = grpc.ssl_channel_credentials(root_certificates=server_cert)
            exporter = OTLPMetricExporter(
                endpoint=endpoint,
                credentials=credentials,
                preferred_temporality={
                    Counter: AggregationTemporality.DELTA,
                    Histogram: AggregationTemporality.DELTA,
                },
            )
            self._logger.info("OTLP gRPC exporter configured with TLS for %s", endpoint)
            return _CircuitBreakerExporter(exporter, self._logger)

        except Exception as error:
            self._logger.info(
                "Failed to configure OTLP exporter: %s",
                _safe_exception_str(error),
            )
            return None

    def register_instrument(
        self, callback: Callable[[Meter], Instrument]
    ) -> Optional[Instrument]:
        """Create a custom instrument using the service's meter.

        Passes the internal ``Meter`` to *callback* and returns whatever the
        callback creates.  If the service failed to initialise (e.g. because
        ``ta_name`` could not be determined), the meter is ``None`` and this
        method returns ``None`` without invoking the callback.

        Always guard the returned value against ``None`` before calling it, for
        the same reason you guard ``event_count_counter``.

        Args:
            callback: A callable that receives the ``Meter`` and returns a new
                instrument (Counter, Histogram, Gauge, etc.).

        Returns:
            The instrument created by *callback*, or ``None`` if the meter is
            not available.

        Example::

            latency = obs.register_instrument(
                lambda meter: meter.create_histogram(
                    name="my_ta.request.latency",
                    description="Latency of outbound API requests",
                    unit="s",
                )
            )

            if latency:
                latency.record(elapsed, {ATTR_MODINPUT_NAME: stanza_name})
        """
        if self._meter is None:
            return None
        return callback(self._meter)

    def flush(self, timeout_millis: float = 30_000) -> None:
        """Force-flush all metric readers.

        Blocks until all buffered data points have been handed off to their
        exporters or *timeout_millis* elapses.  Call this before the modular
        input process exits to avoid dropping the last batch of metrics.

        Prefer using :class:`StanzaObservabilityRecorder` as a context manager
        rather than calling this method directly — it calls
        :meth:`StanzaObservabilityRecorder.flush` on exit automatically.

        Args:
            timeout_millis: Maximum time to wait for exporters to drain, in
                milliseconds.  Defaults to 30 seconds.
        """
        if self._provider is None:
            return
        try:
            self._provider.force_flush(timeout_millis=int(timeout_millis))
        except Exception as error:
            self._logger.info("Failed to flush metrics: %s", _safe_exception_str(error))


_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1


def _is_encodable_str(value: str) -> bool:
    # Caller guarantees type(value) is str.
    try:
        value.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False


def _is_safe_identifier_str(value: str) -> bool:
    return _is_encodable_str(value) and "\n" not in value and "\r" not in value


def _count_error(value) -> Optional[str]:
    """Return None for a valid event/byte count, else a safe reason string."""
    if type(value) is not int:
        return f"expected int, got {_sanitize_for_log(type(value).__name__)}"
    if value < 0:
        return "count is negative"
    if value > _INT64_MAX:
        return f"count exceeds int64 range ({value.bit_length()} bits)"
    return None


def _attr_key_error(key) -> Optional[str]:
    """Return None for a valid attribute key, else a safe reason string."""
    if type(key) is not str:
        return f"expected str key, got {_sanitize_for_log(type(key).__name__)}"
    if not key:
        return "key is empty"
    if not _is_safe_identifier_str(key):
        return "key is not UTF-8 encodable or contains CR/LF"
    return None


def _attr_value_error(value) -> Optional[str]:
    """Return None for a valid attribute value, else a safe reason string."""
    value_type = type(value)
    if value_type is bool:
        return None
    if value_type is int:
        if _INT64_MIN <= value <= _INT64_MAX:
            return None
        return f"int value out of int64 range ({value.bit_length()} bits)"
    if value_type is float:
        return None
    if value_type is str:
        if _is_encodable_str(value):
            return None
        return "value is not UTF-8 encodable"
    return f"unsupported value type: {_sanitize_for_log(value_type.__name__)}"


class StanzaObservabilityRecorder:
    """Stanza-scoped observability recorder backed by a shared ``ObservabilityService``.

    One ``ObservabilityService`` is created per *modinput_type* per process and
    cached in :attr:`_instances` for the lifetime of the process.  Every
    ``StanzaObservabilityRecorder`` for the same *modinput_type* shares that
    service regardless of how many stanzas are active, so the OTLP connection
    and ``MeterProvider`` are only initialised once.

    Each recorder instance is bound to a single *stanza_name*, which is
    automatically attached as the ``"splunk.modinput.name"`` attribute on every
    recorded data point.

    **Best practices:**

    - Use as a context manager (``with`` statement) so that :meth:`flush` is
      always called when the stanza collection loop exits, even on exceptions.
    - Pass the same *modinput_type* string for all stanzas of the same input
      type.  The string should be lowercase, hyphenated, and stable across
      restarts (e.g. ``"event-hub"``).
    - Do not store the recorder beyond the lifetime of a single stanza
      collection cycle — create a new instance for each run.
    - Register custom instruments via :meth:`register_instrument` on the
      recorder instance rather than accessing the underlying service directly.
    - :class:`StanzaObservabilityRecorder` is **thread-safe** at the singleton
      level (``_lock`` protects ``_instances``), but individual recorder
      instances are not meant to be shared across threads.

    **Typical usage**::

        import logging
        from solnlib.observability import StanzaObservabilityRecorder

        logger = logging.getLogger(__name__)

        def collect(stanza_name: str) -> None:
            with StanzaObservabilityRecorder("my-input", logger, stanza_name) as obs:
                events = fetch_events()
                obs.record(len(events), sum(len(e) for e in events))

    **Custom instrument** (e.g. latency histogram)::

        from solnlib.observability import StanzaObservabilityRecorder, ATTR_MODINPUT_NAME

        with StanzaObservabilityRecorder("my-input", logger, stanza_name) as obs:
            latency_histogram = obs.register_instrument(
                lambda meter: meter.create_histogram(
                    name="my_ta.request.latency",
                    description="Latency of outbound API requests",
                    unit="s",
                )
            )
            # ... collect events ...
            if latency_histogram:
                latency_histogram.record(elapsed, {ATTR_MODINPUT_NAME: stanza_name})
    """

    _instances: ClassVar[dict[str, ObservabilityService]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        modinput_type: str,
        logger: _Logger,
        stanza_name: str,
    ) -> None:
        """Initialise a stanza-scoped recorder.

        Gets or creates the shared :class:`ObservabilityService` for
        *modinput_type* (singleton per process), then emits a zero baseline
        on both built-in counters so that the metric series is visible in
        dashboards from the very first collection cycle even when no events
        were ingested.

        Args:
            modinput_type: Low-cardinality identifier for the input type,
                e.g. ``"event-hub"``.  All recorders for the same input type
                share a single ``ObservabilityService``.
            logger: Python logger used both for ``ObservabilityService``
                diagnostics and for the :class:`LoggerMetricExporter` that
                is automatically added as an extra exporter.
            stanza_name: The name of the input stanza being collected (e.g.
                ``"my_stanza"``).  Attached as ``"splunk.modinput.name"``
                on every recorded data point.
        """
        self._logger = logger
        if type(modinput_type) is not str or not _is_safe_identifier_str(modinput_type):
            raise TypeError(
                "modinput_type must be a str without CR/LF, got "
                f"{_sanitize_for_log(type(modinput_type).__name__)}"
            )
        if type(stanza_name) is not str or not _is_safe_identifier_str(stanza_name):
            raise TypeError(
                "stanza_name must be a str without CR/LF, got "
                f"{_sanitize_for_log(type(stanza_name).__name__)}"
            )
        self._stanza_name = stanza_name
        self._service = self._get_or_create_service(modinput_type, logger)
        self._emit_zero_baseline()

    @classmethod
    def _get_or_create_service(
        cls, modinput_type: str, logger: _Logger
    ) -> ObservabilityService:
        """Return the cached service for *modinput_type*, creating it if needed.

        Thread-safe: uses ``_lock`` to ensure exactly one
        ``ObservabilityService`` is created per *modinput_type* even when
        multiple stanzas are initialised concurrently at process start.
        """
        with cls._lock:
            if modinput_type not in cls._instances:
                cls._instances[modinput_type] = ObservabilityService(
                    modinput_type=modinput_type,
                    logger=logger,
                    extra_exporters=[LoggerMetricExporter(logger)],
                )
        return cls._instances[modinput_type]

    def register_instrument(
        self, callback: Callable[[Meter], Instrument]
    ) -> Optional[Instrument]:
        """Create a custom instrument on the shared meter.

        Delegates to :meth:`ObservabilityService.register_instrument`.  The
        instrument is registered on the process-wide ``MeterProvider``, so it
        is shared across all recorders for the same *modinput_type*.  Calling
        this method on any recorder instance for a given *modinput_type* is
        equivalent — register each instrument only once.

        Returns ``None`` when :class:`ObservabilityService` failed to
        initialise (e.g. because ``ta_name`` could not be determined).  Always
        guard the returned value before recording::

            latency_histogram = obs.register_instrument(
                lambda meter: meter.create_histogram(
                    name="my_ta.request.latency",
                    description="Latency of outbound API requests",
                    unit="s",
                )
            )
            if latency_histogram:
                latency_histogram.record(elapsed, {ATTR_MODINPUT_NAME: self._stanza_name})

        Args:
            callback: Callable that receives the ``Meter`` and returns a new
                instrument (Counter, Histogram, Gauge, etc.).

        Returns:
            The instrument created by *callback*, or ``None``.
        """
        return self._service.register_instrument(callback)

    def record(
        self,
        event_count: int,
        byte_count: int,
        extra_attrs: Optional[dict] = None,
    ) -> None:
        """Add *event_count* and *byte_count* to the built-in counters.

        The ``"splunk.modinput.name"`` attribute is always set to the
        *stanza_name* supplied at construction time and cannot be overridden by
        *extra_attrs*.  This preserves the stanza-scoped guarantee — every data
        point is unambiguously attributed to the stanza that recorded it.

        Silently no-ops if either counter is ``None`` (i.e.
        :class:`ObservabilityService` failed to initialise).

        Args:
            event_count: Number of events ingested in this batch.  Pass ``0``
                for an explicit "no events" observation.
            byte_count: Total size of the ingested events in bytes.
            extra_attrs: Optional dict of additional OpenTelemetry attributes
                to attach to both data points.  Keys must be strings; values
                must be strings, booleans, or numbers.  Avoid high-cardinality
                keys such as user IDs or GUIDs.

        Example::

            obs.record(
                event_count=len(events),
                byte_count=sum(len(e) for e in events),
                extra_attrs={"my_ta.partition": partition_id},
            )
        """
        attrs = {}
        if extra_attrs is not None:
            if type(extra_attrs) is not dict:
                self._logger.info(
                    "Ignoring extra_attrs: expected dict or None, got %s",
                    _sanitize_for_log(type(extra_attrs).__name__),
                )
            else:
                for key, value in extra_attrs.items():
                    key_error = _attr_key_error(key)
                    if key_error is not None:
                        self._logger.info(
                            "Ignoring invalid attribute: %s", key_error
                        )
                        continue
                    value_error = _attr_value_error(value)
                    if value_error is not None:
                        self._logger.info(
                            "Ignoring invalid value for attribute %r: %s",
                            key,
                            value_error,
                        )
                        continue
                    attrs[key] = value
        attrs[ATTR_MODINPUT_NAME] = self._stanza_name

        event_count_error = _count_error(event_count)
        if event_count_error is not None:
            self._logger.info("Skipping invalid event_count: %s", event_count_error)
        elif self._service.event_count_counter:
            self._service.event_count_counter.add(event_count, attributes=attrs)

        byte_count_error = _count_error(byte_count)
        if byte_count_error is not None:
            self._logger.info("Skipping invalid byte_count: %s", byte_count_error)
        elif self._service.event_bytes_counter:
            self._service.event_bytes_counter.add(byte_count, attributes=attrs)

    def flush(self) -> None:
        """Force-flush all metric readers.

        Delegates to :meth:`ObservabilityService.flush` (which calls
        ``MeterProvider.force_flush()`` internally).  Called automatically by
        ``__exit__`` when the recorder is used as a context manager, so you
        rarely need to call this directly.

        Call it explicitly only when you are not using the context manager and
        need to guarantee delivery before the process exits::

            obs = StanzaObservabilityRecorder("my-input", logger, stanza_name)
            try:
                obs.record(len(events), total_bytes)
            finally:
                obs.flush()
        """
        self._service.flush()

    def __enter__(self) -> "StanzaObservabilityRecorder":
        """Return *self* to support the ``with`` statement."""
        return self

    def __exit__(self, *_) -> bool:
        """Flush all metric readers and allow exceptions to propagate.

        Returns ``False`` so any exception raised inside the ``with`` block
        is re-raised after flushing.
        """
        self.flush()
        return False

    def _emit_zero_baseline(self) -> None:
        """Emit ``add(0)`` on both built-in counters.

        Called once from ``__init__``.  Ensures that the metric series for this
        stanza appears in dashboards and alerting rules from the very first
        collection cycle, even when no events were ingested.  Without this
        baseline, a stanza that has never produced data is indistinguishable
        from a stanza that has never been seen at all.
        """
        self.record(0, 0)
