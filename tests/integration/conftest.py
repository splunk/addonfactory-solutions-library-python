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
