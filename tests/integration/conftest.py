import os
import sys

import pytest

import context


@pytest.fixture(autouse=True, scope="session")
def setup_env():
    # path manipulation get the 'splunk' library for the imports while running on GH Actions
    if "SPLUNK_HOME" in os.environ:
        splunk_home = os.environ["SPLUNK_HOME"]
        lib_dir = os.path.join(splunk_home, "lib")
        # Find the highest available pythonX.Y directory in $SPLUNK_HOME/lib
        python_dirs = sorted(
            [
                d
                for d in os.listdir(lib_dir)
                if d.startswith("python3.") and os.path.isdir(os.path.join(lib_dir, d))
            ],
            key=lambda d: tuple(int(x) for x in d[6:].split(".")),
            reverse=True,
        )
        if python_dirs:
            sys.path.append(os.path.join(lib_dir, python_dirs[0], "site-packages"))


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
