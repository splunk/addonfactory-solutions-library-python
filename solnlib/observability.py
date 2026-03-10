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

"""OpenTelemetry observability utilities for Splunk add-ons.

This module provides two public components:

- :class:`LoggerMetricExporter` — an OpenTelemetry ``MetricExporter`` that
  writes every exported data point to a standard Python logger.  It is useful
  for local development, debugging, and as a fallback when the Spotlight
  collector is not available.

- :class:`ObservabilityService` — a high-level wrapper that wires up a
  ``MeterProvider`` and creates the two mandatory event counters required by
  every Splunk add-on modular input.  It automatically tries to connect to the
  Splunk Spotlight OTLP collector and falls back silently when it is not
  reachable, so callers never have to handle observability failures themselves.

Typical usage::

    import logging
    from solnlib.observability import LoggerMetricExporter, ObservabilityService, ATTR_MODINPUT_NAME

    logger = logging.getLogger(__name__)

    obs = ObservabilityService(
        modinput_type="my-input",
        logger=logger,
        ta_name="my_ta",
        ta_version="1.0.0",
        extra_exporters=[LoggerMetricExporter(logger)],
    )

    # In your event collection loop:
    if obs.event_count_counter:
        obs.event_count_counter.add(
            len(events), {ATTR_MODINPUT_NAME: stanza_name}
        )
    if obs.event_bytes_counter:
        obs.event_bytes_counter.add(
            total_bytes, {ATTR_MODINPUT_NAME: stanza_name}
        )
"""

import json
import logging
import os
import ssl
import urllib.request
from typing import Callable, List, Optional, Tuple, Union
from typing_extensions import TypeAlias
import grpc
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
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

_Logger: TypeAlias = Union[logging.Logger, logging.LoggerAdapter]

_SPOTLIGHT_SIDECAR_NAME = "spotlight-collector"
_SPOTLIGHT_SERVICE_NAME = "spotlight_telemetry"
_SERVICE_NAMESPACE = "splunk.addon"

ATTR_MODINPUT_NAME = "splunk.modinput.name"


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
        except Exception as e:
            self._logger.error("Failed to export metrics: %s", e, exc_info=True)
            return MetricExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """No-op shutdown — the underlying logger needs no teardown."""

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Flush is a no-op for a synchronous logger; always returns
        ``True``."""
        return True


class ObservabilityService:
    """OpenTelemetry observability service for a Splunk modular input.

    Sets up a ``MeterProvider`` with two built-in event counters and,
    when the Spotlight collector is reachable, an OTLP gRPC exporter.
    Initialisation failures are caught and logged as warnings so that a
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
        extra_exporters: Optional[List[MetricExporter]] = None,
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

        try:
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

            metric_readers: List[PeriodicExportingMetricReader] = []
            otlp_exporter = self._create_otlp_exporter()
            if otlp_exporter:
                metric_readers.append(PeriodicExportingMetricReader(otlp_exporter))
                self._logger.info("OTLP gRPC exporter added to MeterProvider")
            for exporter in extra_exporters or []:
                metric_readers.append(PeriodicExportingMetricReader(exporter))

            provider = MeterProvider(resource=resource, metric_readers=metric_readers)
            self._meter = provider.get_meter(ta_name, ta_version)

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
        except Exception as e:
            self._logger.warning("Failed to initialise ObservabilityService: %s", e)

    def _read_ta_info(self) -> Tuple[Optional[str], Optional[str]]:
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
        except Exception as e:
            self._logger.warning("Failed to read TA info from app.conf: %s", e)
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
        except Exception as e:
            self._logger.warning(
                "Failed to read IPC broker port from server.conf: %s", e
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
            self._logger.warning("IPC broker port not found in server.conf")
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
                self._logger.warning(
                    "IPC broker discovery returned unsuccessful response: %s", data
                )
                return None
            port = str(data["port"])
            self._logger.info("Discovered OTLP port via IPC broker: %s", port)
            return port
        except Exception as e:
            self._logger.warning("IPC broker OTLP port discovery failed: %s", e)
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
        """Create a TLS-secured OTLP gRPC exporter targeting the Spotlight
        collector.

        The collector's server certificate is read from
        ``$SPLUNK_HOME/var/packages/data/spotlight-collector/server.crt``
        (defaults to ``/opt/splunk`` when ``SPLUNK_HOME`` is not set).

        Returns the configured exporter, or ``None`` when:

        - The OTLP port cannot be resolved (see :meth:`_resolve_otlp_port`).
        - The certificate file does not exist.
        - Any other exception occurs during exporter construction.
        """
        try:
            splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
            otel_port = self._resolve_otlp_port()

            self._logger.info(
                "OTLP configuration: otel_port=%s, SPLUNK_HOME=%s",
                otel_port,
                splunk_home,
            )

            if not otel_port:
                self._logger.warning(
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
                self._logger.error(
                    "OTel Collector certificate not found at %s, OTLP export disabled",
                    cert_file,
                )
                return None

            with open(cert_file, "rb") as f:
                server_cert = f.read()

            credentials = grpc.ssl_channel_credentials(root_certificates=server_cert)
            exporter = OTLPMetricExporter(endpoint=endpoint, credentials=credentials)
            self._logger.info("OTLP gRPC exporter configured with TLS for %s", endpoint)
            return exporter

        except Exception as e:
            self._logger.warning(
                "Failed to configure OTLP exporter: %s", e, exc_info=True
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
