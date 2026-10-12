# Asynchronous observability flush with bounded exit grace

## Context

`ObservabilityService.flush()` currently calls `MeterProvider.force_flush()` on
the caller's thread. A missing or slow OTLP collector can therefore delay a
modular input at every `StanzaObservabilityRecorder.flush()` or context-manager
exit. OpenTelemetry's `MeterProvider` also registers a synchronous `atexit`
shutdown by default, so moving only `force_flush()` to another thread would
still leave process exit potentially blocked.

## Goals and contract

- Keep `ObservabilityService.flush(timeout_millis=30_000)` and
  `StanzaObservabilityRecorder.flush()` callable without changing their return
  types. `flush()` schedules export work and returns promptly; it no longer
  confirms delivery before returning. The timeout remains the budget passed
  to the background `force_flush()` call, not a wait on the caller's thread.
- Preserve OTel's periodic export while the process is alive.
- On normal interpreter exit, give pending work and a final OTel shutdown a
  **single process-wide grace period of at most 5 seconds** in solnlib's exit
  handler. If work is unfinished, allow the process to exit and lose the last
  metrics rather than hold the caller indefinitely.
- Keep telemetry failures auxiliary: log them at INFO and do not raise into
  modular-input code.

This grace period bounds only solnlib's own exit handler. Other application
`atexit` handlers, non-daemon threads, and separately created OTel providers
remain outside its control. Abrupt termination (`SIGKILL`, `os._exit()`, etc.)
does not invoke `atexit` and cannot guarantee a final export.

## Design

Each successfully initialized `ObservabilityService` owns one daemon worker,
started during service initialization. The worker waits for requests and is
the only solnlib thread that calls that service's provider `force_flush()` or
`shutdown()`. A condition-protected pending flag coalesces repeated flush
requests, so callers do not create an unbounded queue or new thread per call.
If a request arrives during an export, the worker performs one further flush
after the current one. A later request may replace the pending timeout budget.

Construct solnlib's `MeterProvider` with `shutdown_on_exit=False`; otherwise
OTel's synchronous exit hook would bypass the grace period. Register one
process-wide solnlib `atexit` handler. It signals shutdown to all service
workers, then joins them against one monotonic 5-second deadline rather than
waiting 5 seconds for each service. A worker that receives shutdown performs
one pending explicit flush, if present, within the remaining grace period,
then calls `provider.shutdown()` once with the remaining budget. This matters
when the periodic reader has an infinite interval: its shutdown does not
perform a final collection. If the worker is already inside a flush, it
finishes that operation before handling the pending request and shutdown; if
the grace period expires, the daemon worker can be abandoned at interpreter
exit. The handler never starts a new thread, which is required on Python
3.12+.

Service initialization that fails before a provider exists does not start a
worker. The existing singleton cache continues to share one service and
worker per modular-input type. Directly constructed services are also tracked
for exit cleanup. Shutdown requests are idempotent; flush requests made after
shutdown begins are ignored. Worker exceptions are caught and logged without
terminating the modular input.

Register an `after_in_child` fork callback. In the child it replaces inherited
manager and service synchronization objects, discards parent worker references,
and starts one fresh daemon worker for each inherited live service before any
child `atexit` handler can run. The parent keeps its workers unchanged. The
callback does not call a provider's exporter or perform network I/O.

## Compatibility and trade-offs

This is an intentional semantic change: a returned `flush()` no longer means
that metrics reached an exporter. Existing callers requiring confirmed
delivery need a separate synchronous API; this change does not silently
promise that guarantee. Normal periodic export continues independently.
The added daemon worker costs one thread per active service. A slow export can
coalesce multiple explicit flush requests, and the final 5-second deadline
can sacrifice data when the collector is unavailable. The exporter circuit
breaker remains unchanged and does not itself make flush non-blocking.

## Verification

Add deterministic unit tests for prompt return under a blocked exporter,
coalescing, follow-up requests, exception logging, provider absence, shutdown
idempotency, and the single deadline across multiple services. Add subprocess
tests for normal exit with successful final delivery and a blocked exporter
with a shortened test grace period. Exercise the supported Python versions,
including Python 3.13's prohibition on starting threads in `atexit`, and a
fork smoke test where available. Run the observability unit suite and the
repository's broader relevant tests.
