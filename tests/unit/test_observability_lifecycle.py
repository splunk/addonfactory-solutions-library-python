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
"""Process-level regressions that require interpreter shutdown or a real fork."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCENARIO_SCRIPT = (
    Path(__file__).with_name("helpers") / "observability_flush_process.py"
)


def test_interpreter_exit_is_bounded_with_a_blocked_otel_export():
    # Arrange
    env = dict(os.environ, PYTHONPATH=str(_REPO_ROOT))
    start = time.monotonic()

    # Act
    result = subprocess.run(
        [sys.executable, str(_SCENARIO_SCRIPT), "blocked-otel-exit"],
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
    )
    elapsed = time.monotonic() - start

    # Assert
    assert result.returncode == 0, result.stderr
    assert "MAIN_DONE" in result.stdout
    assert "OTEL_EXPORT_ENTERED" in result.stdout
    assert elapsed < 3


@pytest.mark.skipif(not hasattr(os, "fork"), reason="fork is unavailable")
def test_child_gets_fresh_worker_after_fork():
    # Arrange
    env = dict(os.environ, PYTHONPATH=str(_REPO_ROOT))

    # Act
    result = subprocess.run(
        [sys.executable, str(_SCENARIO_SCRIPT), "fork-worker"],
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
    )

    # Assert
    assert result.returncode == 0, result.stderr
    assert "CHILD_FRESH_WORKER=True" in result.stdout
    assert "PARENT_WORKER_ALIVE=True" in result.stdout
