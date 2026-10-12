# Asynchronous Observability Flush Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make solnlib's public metric `flush()` non-blocking while allowing one process-wide 5-second grace period for final metric export.

**Architecture:** A private daemon worker per initialized observability service serializes explicit flush and final provider shutdown. A process-wide registry registers one `atexit` hook, signals all workers, and joins them against a single monotonic deadline; solnlib-created OTel providers disable their own synchronous exit hook.

**Tech Stack:** Python 3.9–3.13, OpenTelemetry Python SDK >=1.39.1,<2, pytest, `threading`, `atexit`.

**Spec:** `docs/superpowers/specs/2026-10-12-async-observability-flush-design.md`

## Global Constraints

- Preserve `ObservabilityService.flush(timeout_millis: float = 30_000) -> None` and `StanzaObservabilityRecorder.flush() -> None` signatures while documenting the changed asynchronous semantics.
- Keep periodic OTel export; use `MeterProvider(shutdown_on_exit=False)` only for providers constructed by solnlib.
- Give all solnlib workers one total 5-second grace period at normal exit, not 5 seconds each; no thread creation inside `atexit`.
- Keep telemetry failures at INFO and never propagate them into modular-input code.
- Treat pending final metrics as lossy after the grace period; unrelated `atexit` handlers and non-daemon threads are outside this guarantee.
- Keep existing untracked files untouched. Edit only the files listed below and stage/commit only intended files.

## File structure

- Create `solnlib/_observability_flush.py`: private worker, registry, process-exit and fork lifecycle; independent of `observability.py` to avoid growing its already-large public module.
- Create `tests/unit/test_observability_flush.py`: deterministic worker/registry/concurrency tests and subprocess exit/fork smoke tests.
- Modify `solnlib/observability.py`: wire the private manager into `ObservabilityService`, disable OTel's own exit handler, and update public docstrings.
- Modify `tests/unit/test_observability.py`: replace synchronous-flush assertions with asynchronous assertions and cover recorder compatibility.

---

### Task 1: Daemon worker and flush coalescing

**Files:**
- Create: `solnlib/_observability_flush.py`
- Create: `tests/unit/test_observability_flush.py`

**Interfaces:**
- Produces: `_AsyncFlushController(provider, logger, format_error)`, `request_flush(timeout_millis: float) -> None`, `request_shutdown(deadline: float) -> None`, `join_until(deadline: float) -> None`, `restart_after_fork() -> None`.
- Consumes: an OTel-like provider exposing `force_flush(timeout_millis=...)` and `shutdown(timeout_millis=...)`, a logger with `info`, and a safe exception formatter.

- [ ] **Step 1: Write failing tests** in `tests/unit/test_observability_flush.py` for prompt return and coalescing. Use `threading.Event` gates so no network or sleeps are needed:

```python
import logging
import threading
import time
from unittest.mock import MagicMock

from solnlib._observability_flush import _AsyncFlushController


def test_request_flush_returns_while_export_is_blocked():
    entered = threading.Event()
    release = threading.Event()
    provider = MagicMock()

    def blocked_flush(**kwargs):
        entered.set()
        assert release.wait(2)

    provider.force_flush.side_effect = blocked_flush
    controller = _AsyncFlushController(provider, MagicMock(spec=logging.Logger), str)
    try:
        start = time.monotonic()
        controller.request_flush(30_000)
        assert time.monotonic() - start < 0.2
        assert entered.wait(1)
        provider.force_flush.assert_called_once_with(timeout_millis=30_000)
    finally:
        release.set()
        controller.request_shutdown(time.monotonic() + 1)
        controller.join_until(time.monotonic() + 1)


def test_repeated_requests_during_export_coalesce_to_one_followup():
    entered = threading.Event()
    release = threading.Event()
    second_done = threading.Event()
    provider = MagicMock()

    def flush(**kwargs):
        if provider.force_flush.call_count == 1:
            entered.set()
            assert release.wait(2)
        else:
            second_done.set()

    provider.force_flush.side_effect = flush
    controller = _AsyncFlushController(provider, MagicMock(spec=logging.Logger), str)
    try:
        controller.request_flush(30_000)
        assert entered.wait(1)
        controller.request_flush(10_000)
        controller.request_flush(5_000)
        release.set()
        assert second_done.wait(1)
        assert provider.force_flush.call_count == 2
        assert provider.force_flush.call_args_list[-1].kwargs == {"timeout_millis": 5_000}
    finally:
        release.set()
        controller.request_shutdown(time.monotonic() + 1)
        controller.join_until(time.monotonic() + 1)
```

- [ ] **Step 2: Verify red.** Run `. .venv/bin/activate && pytest tests/unit/test_observability_flush.py -q`. Expect import failure because the private module does not exist.
- [ ] **Step 3: Implement the worker** in `solnlib/_observability_flush.py` with one pending timeout slot; never hold its condition across an OTel call:

```python
import threading
import time
from typing import Callable


class _AsyncFlushController:
    def __init__(self, provider, logger, format_error: Callable[[BaseException], str]):
        self._provider = provider
        self._logger = logger
        self._format_error = format_error
        self._condition = threading.Condition()
        self._pending_timeout = None
        self._shutdown_deadline = None
        self._worker = threading.Thread(target=self._run, name="SolnlibMetricFlush", daemon=True)
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
                self._pending_timeout = None
                self._condition.notify()

    def join_until(self, deadline: float) -> None:
        self._worker.join(timeout=max(0.0, deadline - time.monotonic()))

    def _run(self) -> None:
        while True:
            with self._condition:
                while self._pending_timeout is None and self._shutdown_deadline is None:
                    self._condition.wait()
                deadline = self._shutdown_deadline
                timeout = self._pending_timeout
                self._pending_timeout = None
            if deadline is not None:
                try:
                    remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
                    self._provider.shutdown(timeout_millis=remaining_ms)
                except Exception as error:
                    self._logger.info("Failed to shut down metrics: %s", self._format_error(error))
                return
            try:
                self._provider.force_flush(timeout_millis=timeout)
            except Exception as error:
                self._logger.info("Failed to flush metrics: %s", self._format_error(error))

    def restart_after_fork(self) -> None:
        self._condition = threading.Condition()
        self._pending_timeout = None
        self._shutdown_deadline = None
        self._worker = threading.Thread(target=self._run, name="SolnlibMetricFlush", daemon=True)
        self._worker.start()
```

- [ ] **Step 4: Add error/idempotency tests** below the first tests, then run `. .venv/bin/activate && pytest tests/unit/test_observability_flush.py -q` and expect PASS:

```python
def test_worker_logs_export_error_without_raising_to_caller():
    logged = threading.Event()
    provider = MagicMock()
    provider.force_flush.side_effect = RuntimeError("boom")
    logger = MagicMock(spec=logging.Logger)
    logger.info.side_effect = lambda *args: logged.set()
    controller = _AsyncFlushController(provider, logger, str)
    try:
        controller.request_flush(30_000)
        assert logged.wait(1)
        assert "boom" in logger.info.call_args.args[-1]
    finally:
        controller.request_shutdown(time.monotonic() + 1)
        controller.join_until(time.monotonic() + 1)


def test_shutdown_is_once_and_later_flush_is_ignored():
    provider = MagicMock()
    controller = _AsyncFlushController(provider, MagicMock(spec=logging.Logger), str)
    deadline = time.monotonic() + 1
    controller.request_shutdown(deadline)
    controller.request_shutdown(deadline)
    controller.join_until(deadline)
    controller.request_flush(30_000)
    provider.shutdown.assert_called_once()
    provider.force_flush.assert_not_called()
```
- [ ] **Step 5: Commit only these two files** with `git add -- solnlib/_observability_flush.py tests/unit/test_observability_flush.py` and `git commit -m "feat: add async metric flush worker"`.

### Task 2: One process-wide exit deadline and fork reset

**Files:**
- Modify: `solnlib/_observability_flush.py`
- Modify: `tests/unit/test_observability_flush.py`

**Interfaces:**
- Consumes: `_AsyncFlushController` from Task 1.
- Produces: module-level `_register_controller(provider, logger, format_error) -> _AsyncFlushController` backed by `_FlushRegistry`; `_shutdown_all()` is the `atexit` entry point.

- [ ] **Step 1: Write failing registry tests** in the same test file. Use a local registry instance so tests never shut down production's module-level registry:

```python
from solnlib import _observability_flush as flushmod


def test_exit_budget_is_shared_by_two_controllers(monkeypatch):
    monkeypatch.setattr(flushmod, "_EXIT_GRACE_SECONDS", 0.05)
    release = threading.Event()
    entered = [threading.Event(), threading.Event()]
    controllers = []
    registry = flushmod._FlushRegistry()
    for gate in entered:
        provider = MagicMock()
        provider.shutdown.side_effect = lambda gate=gate, **kwargs: (gate.set(), release.wait(2))
        controller = _AsyncFlushController(provider, MagicMock(spec=logging.Logger), str)
        registry._controllers.append(controller)
        controllers.append(controller)
    try:
        start = time.monotonic()
        registry.shutdown_all()
        assert time.monotonic() - start < 0.2
        assert all(gate.wait(1) for gate in entered)
    finally:
        release.set()
        for controller in controllers:
            controller.join_until(time.monotonic() + 1)


def test_one_atexit_registration_for_multiple_controllers(monkeypatch):
    register = MagicMock()
    monkeypatch.setattr(flushmod.atexit, "register", register)
    if hasattr(flushmod.os, "register_at_fork"):
        monkeypatch.setattr(flushmod.os, "register_at_fork", MagicMock())
    registry = flushmod._FlushRegistry()
    registry.add(MagicMock())
    registry.add(MagicMock())
    register.assert_called_once_with(flushmod._shutdown_all)
```
- [ ] **Step 2: Verify red.** Run `. .venv/bin/activate && pytest tests/unit/test_observability_flush.py -q` and confirm `_register_controller`/`_shutdown_all` are missing.
- [ ] **Step 3: Implement the registry** in the private module. Use a global registry object and these exact operations; guard `os.register_at_fork` for platforms without fork:

```python
import atexit
import os

_EXIT_GRACE_SECONDS = 5.0


class _FlushRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._controllers = []
        self._registered = False

    def add(self, controller):
        with self._lock:
            if not self._registered:
                atexit.register(_shutdown_all)
                if hasattr(os, "register_at_fork"):
                    os.register_at_fork(after_in_child=self._after_fork_child)
                self._registered = True
            self._controllers.append(controller)

    def shutdown_all(self):
        deadline = time.monotonic() + _EXIT_GRACE_SECONDS
        with self._lock:
            controllers = tuple(self._controllers)
        for controller in controllers:
            controller.request_shutdown(deadline)
        for controller in controllers:
            controller.join_until(deadline)

    def _after_fork_child(self):
        self._lock = threading.Lock()
        for controller in self._controllers:
            controller.restart_after_fork()


_registry = _FlushRegistry()


def _register_controller(provider, logger, format_error):
    controller = _AsyncFlushController(provider, logger, format_error)
    _registry.add(controller)
    return controller


def _shutdown_all():
    _registry.shutdown_all()
```

- [ ] **Step 4: Verify green** with `. .venv/bin/activate && pytest tests/unit/test_observability_flush.py -q`; verify the shared deadline and single registration assertions.
- [ ] **Step 5: Commit only these two files** with `git add -- solnlib/_observability_flush.py tests/unit/test_observability_flush.py` and `git commit -m "feat: bound metric shutdown across services"`.

### Task 3: Wire the public solnlib API and document the contract change

**Files:**
- Modify: `solnlib/observability.py:45-65,410-465,713-733,1015-1046`
- Modify: `tests/unit/test_observability.py:603-615,947-974,1557-1570,1730-1760`

**Interfaces:**
- Consumes: `_register_controller` and `_AsyncFlushController.request_flush` from Tasks 1–2.
- Produces: unchanged public method signatures, but asynchronous `flush()` semantics and `MeterProvider(..., shutdown_on_exit=False)`.

- [ ] **Step 1: Replace the old synchronous test** with this integration test in `tests/unit/test_observability.py`. Task 1 separately proves that the real controller runs exports off-thread:

```python
def test_flush_schedules_without_calling_provider_on_caller(logger, monkeypatch):
    controller = MagicMock()
    provider_cls = MagicMock()
    monkeypatch.setattr("solnlib.observability.MeterProvider", provider_cls)
    monkeypatch.setattr(
        "solnlib.observability.ObservabilityService._create_otlp_exporter",
        lambda self: None,
    )
    monkeypatch.setattr(
        "solnlib.observability._register_controller",
        lambda provider, logger, formatter: controller,
    )
    svc = ObservabilityService("test-input", logger, ta_name="my_ta", ta_version="1.0.0")
    svc.flush(timeout_millis=5000)
    controller.request_flush.assert_called_once_with(5000)
    provider_cls.return_value.force_flush.assert_not_called()
    assert provider_cls.call_args.kwargs["shutdown_on_exit"] is False
```

  Keep the provider-missing no-op test. Replace the old exception tests with these scheduling-failure assertions; worker-side errors are covered in Task 1:

```python
def test_flush_logs_info_when_scheduling_fails(logger, monkeypatch):
    svc = _make_service(logger, monkeypatch)
    svc._flush_controller = MagicMock()
    svc._flush_controller.request_flush.side_effect = RuntimeError("boom")
    svc.flush()
    assert any("boom" in call.args for call in logger.info.call_args_list)
    logger.warning.assert_not_called()


def test_flush_scheduling_error_uses_safe_str(logger, monkeypatch):
    monkeypatch.setattr("solnlib.observability._safe_exception_str", lambda error: "SAFE")
    svc = _make_service(logger, monkeypatch)
    svc._flush_controller = MagicMock()
    svc._flush_controller.request_flush.side_effect = RuntimeError("boom")
    logger.reset_mock()
    svc.flush()
    assert any("SAFE" in call.args for call in logger.info.call_args_list)
```
- [ ] **Step 2: Verify red.** Run `. .venv/bin/activate && pytest tests/unit/test_observability.py -q`; expect the new thread/constructor assertions to fail.
- [ ] **Step 3: Wire the constructor and method:**

```python
from ._observability_flush import _register_controller

# At the beginning of ObservabilityService.__init__:
self._flush_controller = None

# Replace the provider constructor:
self._provider = MeterProvider(
    resource=resource,
    metric_readers=metric_readers,
    shutdown_on_exit=False,
)

# After counters are created and before the success log:
self._flush_controller = _register_controller(
    self._provider, self._logger, _safe_exception_str
)

# Replace the body of ObservabilityService.flush after the provider guard:
if self._flush_controller is not None:
    self._flush_controller.request_flush(timeout_millis)
```

  Keep the existing `try/except` boundary around `flush()` so scheduling failures stay at INFO. Update `ObservabilityService.flush`, `StanzaObservabilityRecorder.flush`, `__exit__`, and module/class docstrings: returned flush means scheduled attempt, not completed attempt; `timeout_millis` is a worker budget; normal exit may wait up to 5 seconds total.
- [ ] **Step 4: Verify green** with `. .venv/bin/activate && pytest tests/unit/test_observability.py tests/unit/test_observability_flush.py -q`. Ensure existing recorder `with` tests still call `flush()` once and propagate user exceptions.
- [ ] **Step 5: Commit only intended files** with `git add -- solnlib/observability.py tests/unit/test_observability.py` and `git commit -m "feat: make solnlib observability flush nonblocking"`.

### Task 4: Process-exit regression tests and cross-version verification

**Files:**
- Modify: `tests/unit/test_observability_flush.py`
- Modify: `solnlib/_observability_flush.py` only if the tests expose an issue.

**Interfaces:**
- Consumes: final registry and public API from Tasks 1–3.
- Produces: reproducible evidence that normal exit attempts a final export and an unavailable exporter cannot hold solnlib's exit hook beyond its grace period.

- [ ] **Step 1: Add subprocess tests** to `tests/unit/test_observability_flush.py`, with these imports and tests. They use a fake provider and never contact a collector:

```python
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _run_child(script):
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=str(repo_root))
    return subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True,
        env=env, timeout=3,
    )


def test_normal_exit_attempts_final_shutdown_without_explicit_flush():
    result = _run_child("""
import logging
from solnlib._observability_flush import _register_controller
class Provider:
    def force_flush(self, **kwargs): pass
    def shutdown(self, **kwargs): print('FINAL_SHUTDOWN', flush=True)
_register_controller(Provider(), logging.getLogger('test'), str)
""")
    assert result.returncode == 0, result.stderr
    assert "FINAL_SHUTDOWN" in result.stdout


def test_blocked_final_export_uses_shortened_grace_period():
    start = time.monotonic()
    result = _run_child("""
import logging
import threading
import solnlib._observability_flush as flushmod
flushmod._EXIT_GRACE_SECONDS = 0.05
class Provider:
    def force_flush(self, **kwargs): pass
    def shutdown(self, **kwargs): threading.Event().wait(10)
flushmod._register_controller(Provider(), logging.getLogger('test'), str)
""")
    assert result.returncode == 0, result.stderr
    assert time.monotonic() - start < 1.5


@pytest.mark.skipif(not hasattr(os, "fork"), reason="fork is unavailable")
def test_child_gets_fresh_worker_after_fork():
    result = _run_child("""
import logging
import os
import sys
from solnlib._observability_flush import _register_controller
class Provider:
    def force_flush(self, **kwargs): pass
    def shutdown(self, **kwargs): pass
controller = _register_controller(Provider(), logging.getLogger('test'), str)
parent_worker = controller._worker
pid = os.fork()
if pid == 0:
    fresh = controller._worker is not parent_worker and controller._worker.is_alive()
    print('CHILD_FRESH_WORKER=' + str(fresh), flush=True)
    sys.exit(0 if fresh else 2)
_, status = os.waitpid(pid, 0)
print('PARENT_WORKER_ALIVE=' + str(parent_worker.is_alive()), flush=True)
sys.exit(os.waitstatus_to_exitcode(status))
""")
    assert result.returncode == 0, result.stderr
    assert "CHILD_FRESH_WORKER=True" in result.stdout
    assert "PARENT_WORKER_ALIVE=True" in result.stdout
```

- [ ] **Step 2: Run exit/fork tests.** Run `. .venv/bin/activate && pytest tests/unit/test_observability_flush.py -q`. Expect all to pass; if the fork test fails, inspect whether the child's callback ran and repair `restart_after_fork()` before proceeding.
- [ ] **Step 3: Verify both supported runtimes.** Run `. .venv/bin/activate && pytest tests/unit/test_observability.py tests/unit/test_observability_flush.py -q` and `. .venv/bin/activate && pytest tests/unit -q`. Run the focused suite under Python 3.13 if dependencies are installed; otherwise run `python3.13 -m py_compile solnlib/observability.py solnlib/_observability_flush.py` and report that runtime tests on 3.13 remain CI-only. Check `git diff --check` and `git status --short`.
- [ ] **Step 4: Commit only intended files** with `git add -- tests/unit/test_observability_flush.py solnlib/_observability_flush.py` and `git commit -m "test: cover bounded metric export at process exit"`.
