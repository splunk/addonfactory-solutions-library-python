import os
import sys

import pytest

import context


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
