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
"""Executable scenarios for process-level observability regression tests."""

import logging
import os
import sys
import threading

from solnlib import _observability_flush as flushmod


def blocked_otel_exit():
    from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult

    from solnlib.observability import ObservabilityService

    class SlowExporter(MetricExporter):
        def export(self, metrics_data, timeout_millis=10_000, **kwargs):
            print("OTEL_EXPORT_ENTERED", flush=True)
            threading.Event().wait(10)
            return MetricExportResult.SUCCESS

        def shutdown(self, timeout_millis=30_000, **kwargs):
            pass

        def force_flush(self, timeout_millis=10_000):
            return True

    flushmod._EXIT_GRACE_SECONDS = 0.5
    ObservabilityService._create_otlp_exporter = lambda self: None
    service = ObservabilityService(
        "test-input",
        logging.getLogger("test"),
        ta_name="test-ta",
        ta_version="1.0.0",
        extra_exporters=[SlowExporter()],
    )
    service.event_count_counter.add(1)
    print("MAIN_DONE", flush=True)
    return 0


def fork_worker():
    class Provider:
        def force_flush(self, **kwargs):
            pass

        def shutdown(self, **kwargs):
            pass

    controller = flushmod._register_controller(
        Provider(), logging.getLogger("test"), str
    )
    parent_worker = controller._worker
    pid = os.fork()
    if pid == 0:
        fresh = (
            controller._worker is not parent_worker and controller._worker.is_alive()
        )
        print("CHILD_FRESH_WORKER=" + str(fresh), flush=True)
        return 0 if fresh else 2
    _, status = os.waitpid(pid, 0)
    print("PARENT_WORKER_ALIVE=" + str(parent_worker.is_alive()), flush=True)
    return os.waitstatus_to_exitcode(status)


if __name__ == "__main__":
    scenarios = {
        "blocked-otel-exit": blocked_otel_exit,
        "fork-worker": fork_worker,
    }
    sys.exit(scenarios[sys.argv[1]]())
