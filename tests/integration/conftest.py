import os
import sys
import os.path as op
from unittest.mock import MagicMock

import pytest

import context


cur_dir = op.dirname(op.abspath(__file__))


# Mock only once globally, before anything imports `log.py`
mock_msp = MagicMock(return_value=op.sep.join([cur_dir, "data/mock_log"]))
mock_bundle_paths = MagicMock()
mock_bundle_paths.make_splunkhome_path = mock_msp

sys.modules["splunk"] = MagicMock()
sys.modules["splunk.clilib"] = MagicMock()
sys.modules["splunk.clilib.bundle_paths"] = mock_bundle_paths


@pytest.fixture(autouse=True)
def patch_log_msp(monkeypatch):
    """Ensure log.msp is patched in all tests after mocking sys.modules."""
    from solnlib import log  # only import after sys.modules is patched
    monkeypatch.setattr(log, "msp", mock_msp)


@pytest.fixture(autouse=True, scope="session")
def setup_env():
    # path manipulation get the 'splunk' library for the imports while running on GH Actions
    if "SPLUNK_HOME" in os.environ:
        sys.path.append(
            os.path.sep.join(
                [os.environ["SPLUNK_HOME"], "lib", "python3.7", "site-packages"]
            )
        )
        # TODO: 'python3.7' needs to be updated as and when Splunk has new folder for Python.


@pytest.fixture(scope="session")
def session_key():
    return context.get_session_key()


def mock_splunk(monkeypatch):
    def simple_requests(url, *args, **kwargs):
        from splunk.rest import simpleRequest

        return simpleRequest(url, *args, **kwargs)

    def make_splunkn_home(url, *args, **kwargs):
        from splunk.clilib.bundle_paths import make_splunkhome_path

        return make_splunkhome_path(url, *args, **kwargs)

    monkeypatch.setattr("solnlib.splunkenv.simpleRequest", simple_requests)
    monkeypatch.setattr("solnlib.splunkenv.msp", make_splunkn_home)
