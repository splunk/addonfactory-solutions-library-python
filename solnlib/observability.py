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

"""OpenTelemetry observability utilities for Splunk add-ons."""

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
    """MetricExporter that writes each data point to a standard Python
    logger."""

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
        pass

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


class ObservabilityService:
    """OpenTelemetry observability service for a Splunk modular input instance.

    Initialises a MeterProvider backed by a logger exporter (always on) and,
    when available, an OTLP gRPC exporter targeting the Spotlight collector.

    Resource attributes (constant per process, set at construction time):
        splunk.addon.name     = ta_name
        service.namespace     = "splunk.addon"
        splunk.addon.version  = ta_version
        splunk.modinput.type  = modinput_type

    Mandatory instruments (accessible as attributes):
        event_count_counter   -- splunk.addon.events       (Counter, unit "1")
        event_bytes_counter   -- splunk.addon.events.bytes (Counter, unit "By")

    Both counters accept a ``splunk.modinput.name`` data-point attribute that
    callers supply on each ``add()`` call to identify the stanza.  No other
    high-cardinality attributes should be added to these metrics.

    Additional instruments can be created via the public ``meter`` attribute.
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
            modinput_type: Low-cardinality type string for the modular input,
                e.g. ``"event-hub"``.  Used as the ``splunk.modinput.type``
                resource attribute.
            logger: Standard Python logger used for all diagnostic output.
                Typically the caller's own module logger.
            ta_name: TA identifier for ``splunk.addon.name``.  When *None* the
                value is read automatically from ``app.conf``.
            ta_version: TA version for ``splunk.addon.version``.  When *None*
                the value is read automatically from ``app.conf``.
            extra_exporters: Additional MetricExporter instances to include
                alongside the OTLP exporter (e.g. LoggerMetricExporter for
                local debug logging).  Each is wrapped in a
                PeriodicExportingMetricReader automatically.
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
        """Read TA name and version from app.conf via solnlib btool.

        Returns (ta_name, ta_version).  Either value is None when it
        cannot be read (e.g. outside a real Splunk environment).
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
        """Read the IPC broker port from Splunk's server.conf via solnlib
        btool."""
        try:
            stanzas = get_conf_stanzas("server")
            return int(stanzas["ipc_broker"]["port"])
        except Exception as e:
            self._logger.warning(
                "Failed to read IPC broker port from server.conf: %s", e
            )
            return None

    def _discover_otlp_port_via_ipc_broker(self) -> Optional[str]:
        """Discover the OTLP receiver port via the Spotlight IPC broker
        discovery endpoint."""
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
        """Resolve the OTLP receiver port.

        Checks SPOTLIGHT_OTEL_RECEIVER_PORT env var first; falls back to
        IPC broker discovery.
        """
        port = os.environ.get("SPOTLIGHT_OTEL_RECEIVER_PORT")
        if port:
            return port

        self._logger.info(
            "SPOTLIGHT_OTEL_RECEIVER_PORT not set, attempting IPC broker discovery"
        )
        return self._discover_otlp_port_via_ipc_broker()

    def _create_otlp_exporter(self) -> Optional[MetricExporter]:
        """Create an OTLP gRPC exporter for the OTel Collector.

        Returns a wrapped exporter on success, or None if the endpoint
        cannot be determined or the exporter fails to initialise.
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
        """Create an additional instrument using the meter.

        Calls ``callback(meter)`` and returns the result.  If the meter is not
        available (e.g. initialisation failed), returns ``None`` without calling
        the callback.

        Usage::

            histogram = observability.register_instrument(
                lambda meter: meter.create_histogram(
                    name="eventhub.events.latency",
                    description="...",
                    unit="s",
                )
            )
        """
        if self._meter is None:
            return None
        return callback(self._meter)
