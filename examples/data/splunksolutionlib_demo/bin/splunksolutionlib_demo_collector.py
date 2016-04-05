import time
import uuid
from splunksolutionlib import splunkenv
from splunksolutionlib import log
from splunksolutionlib.modular_input import *

log.Logs.set_context(
    directory=splunkenv.make_splunkhome_path(['var', 'log', 'splunk']),
    namespace='splunksolutionlib_demo')
logger = log.Logs().get_logger('collector')


def orphan_handler(md):
    logger.info('Splunksolutionlib demo collector becomes orphan process, will teardown...')
    md._should_exit = True


def teardown_handler(md):
    logger.info('Splunksolutionlib demo collector got teardown signal, will teardown...')
    md._should_exit = True


class SplunksolutionDemoCollector(ModularInput):
    app = 'splunksolutionlib_demo'
    name = 'splunksolutionlib_demo_collector'
    title = 'Splunksolutionlib demo collector'
    description = 'Splunksolutionlib demo collector'

    def __init__(self):
        super(SplunksolutionDemoCollector, self).__init__()
        self._should_exit = False

    def extra_arguments(self):
        return [{'name': 'hec_scheme',
                 'description': 'Splunksolutionlib demo hec scheme',
                 'data_type': Argument.data_type_string,
                 'required_on_create': True},
                {'name': 'hec_host',
                 'description': 'Splunksolutionlib demo hec host',
                 'data_type': Argument.data_type_string,
                 'required_on_create': True},
                {'name': 'hec_port',
                 'description': 'Splunksolutionlib demo hec port',
                 'data_type': Argument.data_type_number,
                 'required_on_create': True},
                {'name': 'hec_token',
                 'description': 'Splunksolutionlib demo hec port',
                 'data_type': Argument.data_type_string,
                 'required_on_edit': True,
                 'required_on_create': True}]

    def do_run(self, inputs):
        logger.info('Splunksolutionlib demo modular input start...')
        logger.info('inputs: %s.', inputs)
        self.register_orphan_handler(orphan_handler, self)
        self.register_teardown_handler(teardown_handler, self)

        event_writer = self.event_writer
        checkpoint = self.checkpoint

        while not self._should_exit:
            tm = time.time()
            data1 = {'id': uuid.uuid4().hex, 'time': tm}
            event1 = Event(data1, time=tm,
                           source='splunksolutionlib_demo',
                           sourcetype='splunksolutionlib_demo')
            data2 = uuid.uuid4().hex
            event2 = Event(data2, time=tm,
                           source='splunksolutionlib_demo',
                           sourcetype='splunksolutionlib_demo')
            event_writer.write_events([event1, event2])
            state = [event1.to_json(), event2.to_json()]
            checkpoint.update('splunksolutionlib_demo_collector_state',
                              state)
            time.sleep(5)
            checkpoint.get('splunksolutionlib_demo_collector_state')
            logger.info('Get checkpoint: event1=%s.', state[0])
            logger.info('Get checkpoint: event2:%s.', state[1])

        logger.info('Splunksolutionlib demo modular input stop...')

if __name__ == '__main__':
    md = SplunksolutionDemoCollector()
    md.execute()
