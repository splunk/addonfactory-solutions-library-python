import os
import os.path as op
import shutil
import sys

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib.modular_input import checkpointer
from solnlib.modular_input.modular_input import ModularInput
from solnlib.modular_input import Argument

checkpoint_dir = op.join(op.dirname(op.abspath(__file__)), '.checkpoint_dir')


def setup_module(module):
    os.mkdir(checkpoint_dir)


def teardown_module(module):
    shutil.rmtree(checkpoint_dir)


# Define orphan process handler
def orphan_handler(md):
    md.should_exit = True


# Define teardown signal handler
def teardown_handler(md):
    md.should_exit = True


# Custom modular input
class CustomModularInput(ModularInput):
    # Override app name
    app = 'UnittestApp'
    # Override modular input name
    name = 'unittest_app_collector'
    # Override modular input scheme title
    title = 'unittest app collector'
    # Override modular input scheme description
    description = 'Unittest app collector'
    # Override modular input use_external_validation
    use_external_validation = True
    # Override modular input use_single_instance
    use_single_instance = False
    # Override use_kvstore_checkpointer
    use_kvstore_checkpointer = False
    # Override use_hec_event_writer
    use_hec_event_writer = False

    # Override extra_arguments function
    def extra_arguments(self):
        return [{'name': 'state',
                 'description': 'Unittest app collector state',
                 'data_type': Argument.data_type_string,
                 'required_on_create': True}]

    def do_validation(self, parameters):
        assert parameters['state'] == 'success'

    # Override do_run function
    def do_run(self, inputs):
        # Register orphan process handler
        self.register_orphan_handler(orphan_handler, self)
        # Register teardown signal handler
        self.register_teardown_handler(teardown_handler, self)

        # Get event writer to write events
        event_writer = self.event_writer
        # Get checkpoint to manage checkpoint
        checkpointer = self.checkpointer

        # Main loop
        while not self.should_exit:
            # Create events
            data1 = {'id': 12345, 'time': 1461394857.301}
            # Use class method of event writer to create a new event
            event1 = event_writer.create_event(data1, time=1461394857.301,
                                               source='unittestapp',
                                               sourcetype='unittestapp')
            event2 = event_writer.create_event('12345', time=1461394857.301,
                                               source='unittestapp',
                                               sourcetype='unittestapp')
            # Use event writer to write events
            event_writer.write_events([event1, event2])
            # Prepare checkpoint state
            state = [str(event1), str(event2)]
            # Save checkpoint
            checkpointer.update('unittest_app_checkpoint', state)
            self.should_exit = True


def test_modular_input(monkeypatch):
    class _MockStdout(object):
        def __init__(self):
            self._buf = ''

        def read(self, size=None):
            content = self._buf
            self._buf = ''
            return content

        def write(self, event):
            if isinstance(event, bytes):
                self._buf += event.decode('utf-8')
            else:
                self._buf += event

        def flush(self):
            pass

    mock_stdout = _MockStdout()
    monkeypatch.setattr(sys, 'stdout', mock_stdout)

    mock_stderr = _MockStdout()
    monkeypatch.setattr(sys, 'stderr', mock_stderr)

    # Create custom modular input
    md = CustomModularInput()

    # Run modular input with '--scheme'
    sys.argv = [None, '--scheme']
    md.execute()
    assert sys.stdout.read() == '<scheme><title>unittest app collector</title><description>Unittest app collector</description><use_external_validation>true</use_external_validation><use_single_instance>false</use_single_instance><streaming_mode>xml</streaming_mode><endpoint><args><arg name="state"><description>Unittest app collector state</description><data_type>string</data_type><required_on_edit>false</required_on_edit><required_on_create>true</required_on_create></arg></args></endpoint></scheme>'

    sys.argv = [None, '--validate-arguments']
    validate_arugments_input = '<items><server_host>lli-mbpr.local</server_host><server_uri>https://127.0.0.1:8089</server_uri><session_key>{session_key}</session_key><checkpoint_dir>{checkpoint_dir}</checkpoint_dir><item name="unittest"><param name="state">success</param></item></items>'.format(session_key=common.SESSION_KEY, checkpoint_dir=checkpoint_dir)
    with open('.validate-arguments.xml', 'w') as fp:
        fp.write(validate_arugments_input)
    mock_stdin = open('.validate-arguments.xml', 'rb')
    monkeypatch.setattr(sys, 'stdin', mock_stdin)
    md.execute()
    mock_stdin.close()
    os.remove('.validate-arguments.xml')

    sys.argv = [None, '--validate-arguments']
    validate_arugments_input = '<items><server_host>lli-mbpr.local</server_host><server_uri>https://127.0.0.1:8089</server_uri><session_key>{session_key}</session_key><checkpoint_dir>{checkpoint_dir}</checkpoint_dir><item name="unittest"><param name="state">fail</param></item></items>'.format(session_key=common.SESSION_KEY, checkpoint_dir=checkpoint_dir)
    with open('.validate-arguments.xml', 'w') as fp:
        fp.write(validate_arugments_input)
    mock_stdin = open('.validate-arguments.xml', 'rb')
    monkeypatch.setattr(sys, 'stdin', mock_stdin)
    # with pytest.raises(AssertionError):
    md.execute()
    mock_stdin.close()
    os.remove('.validate-arguments.xml')

    sys.argv = [None]
    run_input = '<input><server_host>lli-mbpr.local</server_host><server_uri>https://127.0.0.1:8089</server_uri><session_key>{session_key}</session_key><checkpoint_dir>{checkpoint_dir}</checkpoint_dir><configuration><stanza name="unittest_app_collector://test1"><param name="state">success</param></stanza></configuration></input>'.format(session_key=common.SESSION_KEY, checkpoint_dir=checkpoint_dir)
    with open('.run.xml', 'w') as fp:
        fp.write(run_input)
    mock_stdin = open('.run.xml', 'rb')
    monkeypatch.setattr(sys, 'stdin', mock_stdin)
    md.execute()
    assert sys.stdout.read() == '<stream><event><time>1461394857.301</time><source>unittestapp</source><sourcetype>unittestapp</sourcetype><data>{"id": 12345, "time": 1461394857.301}</data></event><event><time>1461394857.301</time><source>unittestapp</source><sourcetype>unittestapp</sourcetype><data>12345</data></event></stream>'
    mock_stdin.close()
    os.remove('.run.xml')

    sys.argv = [None, 'invalid-argument']
    md.execute()


def test_modular_input_create_checkpointer(monkeypatch):
    collections = [0]
    def mock_kvstore_checkpointer_init(self, collection_name,
                                       session_key, app, owner='nobody',
                                       scheme=None, host=None, port=None, **context):
        collections[0] = collection_name

    monkeypatch.setattr(checkpointer.KVStoreCheckpointer, '__init__',
                        mock_kvstore_checkpointer_init)
    md = CustomModularInput()
    md.use_kvstore_checkpointer = True
    md.kvstore_checkpointer_collection_name = 'kv_store_checkpointer_test'
    md.config_name = 'config_test'

    checkpoint = md._create_checkpointer()
    assert collections[0] == 'UnittestApp:config_test:kv_store_checkpointer_test'
    assert isinstance(checkpoint, checkpointer.KVStoreCheckpointer)
