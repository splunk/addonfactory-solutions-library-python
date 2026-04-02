# Release 8.0.0

## Breaking changes

### Python 3.7 and 3.8 are no longer supported

As of version 8.0.0, Python 3.7 and 3.8 are no longer supported.
The minimum required Python version is now **3.9**.

If your add-on runs on Python 3.7 or 3.8, you must upgrade your environment
before upgrading solnlib to 8.0.0.

### New required dependencies

The `observability` module introduces the following new dependencies:

* `opentelemetry-api >=1.39.1,<2`
* `opentelemetry-sdk >=1.39.1,<2`
* `opentelemetry-exporter-otlp-proto-grpc >=1.39.1,<2`
* `grpcio >=1.74.0`

These are installed automatically when installing solnlib via pip.

## New features

### ObservabilityService

A new `solnlib.observability` module has been added. It provides OpenTelemetry
metric instrumentation for Splunk modular inputs, with automatic integration
with the Splunk Spotlight collector.

The module exposes two public components:

* `ObservabilityService` — initializes a `MeterProvider` with two built-in
  event counters and attempts to connect to the local Spotlight OTLP collector.
  Falls back silently when the collector is not available, so observability
  failures never break the add-on.
* `LoggerMetricExporter` — an OpenTelemetry `MetricExporter` that writes
  data points to a Python logger. Useful for local development and debugging.

**Built-in counters:**

| Attribute               | Metric name                   | Unit  |
|-------------------------|-------------------------------|-------|
| `event_count_counter`   | `splunk.addon.events`         | `1`   |
| `event_bytes_counter`   | `splunk.addon.events.bytes`   | `By`  |

**Example usage:**

```python
import logging
from solnlib.observability import ObservabilityService, ATTR_MODINPUT_NAME

logger = logging.getLogger(__name__)

obs = ObservabilityService(
    modinput_type="my-input",
    logger=logger,
    ta_name="my_ta",
    ta_version="1.0.0",
)

# In your event collection loop:
if obs.event_count_counter:
    obs.event_count_counter.add(len(events), {ATTR_MODINPUT_NAME: stanza_name})
if obs.event_bytes_counter:
    obs.event_bytes_counter.add(total_bytes, {ATTR_MODINPUT_NAME: stanza_name})
```

When `ta_name` and `ta_version` are not provided, they are read automatically
from `app.conf` via `get_conf_stanzas`. Pass them explicitly when running
outside a full Splunk environment.

Additional instruments can be registered using `ObservabilityService.register_instrument`.

For full API reference see [observability.py](observability.md).
