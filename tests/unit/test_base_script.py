import builtins
import json
import os
from io import StringIO

import pytest

from solnlib.modular_input import BaseScript


@pytest.fixture()
def file_open_mock(args_content, args_path, monkeypatch):
    _old_open = open

    def _open_mocked(*args, **kwargs):
        if args[0] == args_path:
            return StringIO(json.dumps(args_content))
        return _old_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", _open_mocked)


@pytest.fixture()
def file_exists_mock(monkeypatch, args_path):
    _old_isfile = os.path.isfile

    def _isfile_mocked(*args, **kwargs):
        if args[0] == args_path:
            return True
        return _old_isfile(*args, **kwargs)

    monkeypatch.setattr(os.path, "isfile", _isfile_mocked)


@pytest.fixture()
def example_script():
    class ExampleScript(BaseScript):
        def stream_events(self, inputs, ew):
            pass

    return ExampleScript()


@pytest.fixture
def args_path():
    return os.path.splitext(__file__)[0] + ".args.json"


@pytest.fixture
def args_content():
    return {
        "name": "example_script",
        "description": "Example description",
        "entity": [
            {
                "field": "some_field1",
                "required": True
            },
            {
                "field": "some_field2"
            }
        ]
    }


@pytest.mark.usefixtures("file_exists_mock", "file_open_mock")
def test_base_script_args_file_exists(args_content, example_script):
    assert example_script.args == args_content


def test_base_script_args_file_does_not_exist(example_script):
    assert example_script.args == {}


@pytest.mark.usefixtures("file_exists_mock")
def test_base_script_args_cached(example_script, args_content, monkeypatch, args_path):
    data = {"calls": 0}
    _old_open = open

    def _open_mocked(*args, **kwargs):
        if args[0] == args_path:
            data["calls"] += 1
            return StringIO(json.dumps(args_content))
        return _old_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", _open_mocked)

    assert data["calls"] == 0
    assert example_script.args == args_content
    assert data["calls"] == 1
    assert example_script.args == args_content
    assert data["calls"] == 1


@pytest.mark.usefixtures("file_exists_mock", "file_open_mock")
def test_base_script_scheme(args_content, example_script):
    scheme = example_script.get_scheme()
    assert scheme.title == args_content["name"]
    assert scheme.description == args_content["description"]
    assert len(scheme.arguments) == 3
    assert scheme.arguments[0].name == "name"
    assert scheme.arguments[0].required_on_create

    assert scheme.arguments[1].name == args_content["entity"][0]["field"]
    assert scheme.arguments[1].required_on_create == args_content["entity"][0]["required"]

    assert scheme.arguments[2].name == args_content["entity"][1]["field"]
    assert scheme.arguments[2].required_on_create == False
