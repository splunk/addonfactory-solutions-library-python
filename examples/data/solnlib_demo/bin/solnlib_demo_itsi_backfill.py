import sys
import time
import logging

from solnlib import log
from solnlib.server_info import ServerInfo
from solnlib.modular_input import *

# Set log context
log.Logs.set_context(
    namespace='solnlib_demo',
    root_logger_log_file='itsi_backfill')
# Get named logger
logger = log.Logs().get_logger('itsi_backfill')


# Mock ItsiBackfillCore
class ItsiBackfillCore(object):
    def __init__(self, modular_input, session_key, should_execute, messenger=None):
        self._modular_input = modular_input

    def start(self):
        while not self._modular_input.should_exit:
            logger.info('Solnlib demo itsi backfill manager is running...')
            time.sleep(10)


# Define orphan process handler
def orphan_handler(md):
    logger.info(
        'Solnlib demo itsi backfill manager becomes orphan process, will teardown...')
    md.should_exit = True


# Define teardown signal handler
def teardown_handler(md):
    logger.info('Solnlib demo itsi backfill manager got teardown signal, will teardown...')
    md.should_exit = True


class BackfillModularInputException(Exception):
    pass


class ItsiBackfillModularInput(ModularInput):
    # Override app name
    app = 'solnlib_demo'
    # Override modular input name
    name = 'solnlib_demo_itsi_backfill'
    # Override modular input scheme title
    title = 'Solnlib Demo ITSI Backfill Manager'
    # Override modular input scheme description
    description = 'Supervises long-running backfill jobs that generate summarized KPI metrics from raw data.'
    # Override modular input use_external_validation
    use_external_validation = True
    # Override modular input use_single_instance
    use_single_instance = False
    # Override use_kvstore_checkpointer
    use_kvstore_checkpointer = True
    # Override kvstore_checkpoint_collection_name
    kvstore_checkpointer_collection_name = 'SolnDemoItsiBackfillCheckpoint'
    # Override use_hec_event_writer
    use_hec_event_writer = False

    # Override extra_arguments function
    def extra_arguments(self):
        return [{'name': 'log_level',
                 'description': 'Level of log messages to print to log (ERROR, WARN, INFO, DEBUG)',
                 'data_type': Argument.data_type_string,
                 'required_on_create': False}]

    def do_validation(self, parameters):
        '''Handles external validation for modular input kinds.

        When Splunk calls a modular input script in validation mode, it will
        pass in an XML document giving information about the Splunk instance
        (so you can call back into it if needed) and the name and parameters
        of the proposed input. If this function does not throw an exception,
        the validation is assumed to succeed. Otherwise any errors thrown will
        be turned into a string and logged back to Splunk.

        :param parameters: The parameters of input passed by splunkd.

        :raises Exception: If validation is failed.
        '''

        logger.info('Validate parameters: %s.', parameters)

    def _should_execute(self):
        server_info = ServerInfo(self.session_key,
                                 scheme=self.server_scheme,
                                 host=self.server_host,
                                 port=self.server_port)
        if server_info.is_captain() or not server_info.is_shc_member():
            return True
        else:
            return False

    def _show_message(self, message):
        pass

    def do_run(self, inputs):
        '''Modular input entry.

        :param inputs: Modular inputs, for instance: {
            'stanza_name1': {'log_level': 'INFO'},
            'stanza_name2': {'log_level': 'ERROR'}
            }.
        :type inputs: ``dict``
        '''

        # Single instance mode for safety only, so we only want the
        # first stanza
        input_config = inputs[inputs.keys()[0]]
        level = input_config.get("log_level", 'INFO').upper()
        if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            level = "INFO"
        log.Logs().set_level(logging.getLevelName(level))

        # Main Logic
        logger.info("Running ITSI backfill manager!")

        # Register orphan process handler
        self.register_orphan_handler(orphan_handler, self)
        # Register teardown signal handler
        self.register_teardown_handler(teardown_handler, self)

        if not self._should_execute():
            logger.info('Should not execute on this search head since there '
                        'is another search head with priority to run')
            return

        try:
            backfill_core = ItsiBackfillCore(self,
                                             self.session_key,
                                             self._should_execute(),
                                             messenger=self._show_message)
            backfill_core.start()
        except Exception as e:
            logger.error("Backfill core job raised an exception: %s", e)
            logger.exception(e)

        logger.info("Exiting modinput")
        return

if __name__ == '__main__':
    worker = ItsiBackfillModularInput()
    worker.execute()
    sys.exit(0)
