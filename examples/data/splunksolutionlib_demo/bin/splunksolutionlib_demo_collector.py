import time
import uuid
from splunksolutionlib import splunkenv
from splunksolutionlib import log
from splunksolutionlib.modular_input import *

# Set log context
log.Logs.set_context(
    directory=splunkenv.make_splunkhome_path(['var', 'log', 'splunk']),
    namespace='splunksolutionlib_demo')
# Get named logger
logger = log.Logs().get_logger('collector')


# Define orphan process handler
def orphan_handler(md):
    logger.info('Splunksolutionlib demo collector becomes orphan process, will teardown...')
    md._should_exit = True


# Define teardown signal handler
def teardown_handler(md):
    logger.info('Splunksolutionlib demo collector got teardown signal, will teardown...')
    md._should_exit = True


# Custom modular input
class SplunksolutionDemoCollector(ModularInput):
    # Override app name
    app = 'splunksolutionlib_demo'
    # Override modular input name
    name = 'splunksolutionlib_demo_collector'
    # Override modular input scheme title
    title = 'Splunksolutionlib demo collector'
    # Override modular input scheme description
    description = 'Splunksolutionlib demo collector'
    # Override modular input use_external_validation
    use_external_validation = True
    # Override modular input use_single_instance
    use_single_instance = False
    # Override use_kvstore_checkpoint
    use_kvstore_checkpoint = True
    # Override kvstore_checkpoint_collection_name
    kvstore_checkpoint_collection_name = 'SplunksolutionDemoCollectorCheckpoint'
    # Override use_hec_event_writer
    use_hec_event_writer = False
    # Override hec_token_name
    hec_token_name = 'SplunksolutionDemoCollectorHECToken'

    # Custom init function
    # Notice: base modular input init function must be called.
    def __init__(self):
        super(SplunksolutionDemoCollector, self).__init__()
        self._should_exit = False

    # Override extra_arguments function
    def extra_arguments(self):
        return [{'name': 'state',
                 'description': 'Splunksolutionlib demo collector state',
                 'data_type': Argument.data_type_string,
                 'required_on_create': True},
                {'name': 'timeout',
                 'description': 'Splunksolutionlib demo collector collect data timeout',
                 'data_type': Argument.data_type_number,
                 'required_on_create': True},
                {'name': 'do_check',
                 'description': 'Splunksolutionlib demo collector check collected data flag',
                 'data_type': Argument.data_type_boolean,
                 'required_on_create': True}]

    # Override do_run function
    def do_run(self, inputs):
        logger.info('Splunksolutionlib demo modular input start...')
        logger.info('inputs: %s.', inputs)
        # Register orphan process handler
        self.register_orphan_handler(orphan_handler, self)
        # Register teardown signal handler
        self.register_teardown_handler(teardown_handler, self)

        # Get event writer to write events
        event_writer = self.event_writer
        # Get checkpoint to manage checkpoint
        checkpoint = self.checkpoint

        # Main loop
        while not self._should_exit:
            # Get checkpoint
            state = checkpoint.get('splunksolutionlib_demo_collector_state')
            if state:
                logger.info('Get checkpoint: event1=%s.', state[0])
                logger.info('Get checkpoint: event2:%s.', state[1])

            # Create events
            tm = time.time()
            data1 = {'id': uuid.uuid4().hex, 'time': tm}
            # Use class method of event writer to create a new event
            event1 = event_writer.create_event(data1, time=tm,
                                               source='splunksolutionlib_demo',
                                               sourcetype='splunksolutionlib_demo')
            data2 = uuid.uuid4().hex
            event2 = event_writer.create_event(data2, time=tm,
                                               source='splunksolutionlib_demo',
                                               sourcetype='splunksolutionlib_demo')
            # Use event writer to write events
            event_writer.write_events([event1, event2])
            # Prepare checkpoint state
            state = [str(event1), str(event2)]
            # Save checkpoint
            checkpoint.update('splunksolutionlib_demo_collector_state',
                              state)
            time.sleep(5)

        logger.info('Splunksolutionlib demo modular input stop...')

if __name__ == '__main__':
    # Create custom modular input
    md = SplunksolutionDemoCollector()
    # Run modular input
    md.execute()
