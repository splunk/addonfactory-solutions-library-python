import json
import subprocess
import sys
from textwrap import dedent


def test_base_script(tmp_path):
    args = {
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

    with open(tmp_path / "some_script.args.json", "w") as fp:
        json.dump(args, fp)

    with open(tmp_path / "some_script.py", "w") as fp:
        fp.write(dedent(
            """
            import json
            from solnlib.modular_input import BaseScript
            
            
            class SomeScript(BaseScript):
                def stream_events(self, inputs, ew):
                    pass
            
            
            print(json.dumps(SomeScript().args))
            """
        ))

    proc = subprocess.Popen([sys.executable, str(tmp_path / "some_script.py")], stdout=subprocess.PIPE)
    stdout = proc.communicate()[0].decode()
    assert json.loads(stdout) == args
