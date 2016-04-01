# Copyright 2016 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import logging
import traceback
import urlparse
from abc import ABCMeta, abstractmethod
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from splunklib.modularinput.argument import Argument
from splunklib.modularinput.scheme import Scheme
from splunklib.modularinput.input_definition import InputDefinition
from splunklib.modularinput.validation_definition import ValidationDefinition

from splunksolutionlib import checkpoint
from splunksolutionlib.orphan_process_monitor import OrphanProcessChecker


class ModularInputException(Exception):
    pass


class ModularInput(object):
    __metaclass__ = ABCMeta

    def __init__(self, app, title, description, use_external_validation=False,
                 streaming_mode=Scheme.streaming_mode_xml, use_single_instance=False,
                 use_kvstore_checkpoint=True):
        self._app = app

        # Scheme
        self._scheme = Scheme(title)
        self._scheme.description = description
        self._scheme.use_external_validation = use_external_validation
        self._scheme.streaming_mode = streaming_mode
        self._scheme.use_single_instance = use_external_validation

        # Metadata
        self._server_host = None
        self._server_uri = None
        self._session_key = None
        self._checkpoint_dir = None

        self._use_kvstore_checkpoint = use_kvstore_checkpoint
        self._checkpoint = None

        # Init orphan process checker
        self._orphan_checker = OrphanProcessChecker()

    def _update_metadata(self, metadata):
        self._server_host = metadata['server_host']
        self._server_uri = metadata['server_uri']
        self._session_key = metadata['session_key']
        self._checkpoint_dir = metadata['checkpoint_dir']

    @property
    def is_orphan(self):
        return self._orphan_checker.is_orphan()

    @property
    def server_host(self):
        return self._server_host

    @property
    def server_uri(self):
        return self._server_uri

    @property
    def session_key(self):
        return self._session_key

    @property
    def checkpoint(self):
        if self._checkpoint is None:
            if self._use_kvstore_checkpoint:
                splunkd = urlparse.urlparse(self._server_uri)
                self._checkpoint = checkpoint.KVStoreCheckpoint(
                    self._session_key, self._app, owner='nobody',
                    scheme=splunkd.scheme, host=splunkd.hostname, port=splunkd.port)
            else:
                self._checkpoint = checkpoint.FileCheckpoint(self._checkpoint_dir)

        return self._checkpoint

    def add_argument(self, name, title=None, description=None, validation=None,
                     data_type=Argument.data_type_string, required_on_edit=False,
                     required_on_create=False):
        self._scheme.add_argument(Argument(name, title=title,
                                           description=description,
                                           validation=validation,
                                           data_type=data_type,
                                           required_on_edit=required_on_edit,
                                           required_on_create=required_on_create))

    def do_validation(self, parameters):
        '''Handles external validation for modular input kinds.

        When Splunk calls a modular input script in validation mode, it will
        pass in an XML document giving information about the Splunk instance
        (so you can call back into it if needed) and the name and parameters
        of the proposed input. If this function does not throw an exception,
        the validation is assumed to succeed. Otherwise any errors thrown will
        be turned into a string and logged back to Splunk. The default implementation
        always passes.

        :param parameters: The parameters for the proposed input passed by splunkd.

        :raises Exception: If validation is failed.
        '''

        pass

    @abstractmethod
    def do_run(self, inputs):
        '''Runs this modular input

        :param args: List of command line arguments passed to this script.
        :returns: An integer to be used as the exit value of this program.
        '''

        pass

    def execute(self):
        if len(sys.argv) == 1:
            try:
                input_definition = InputDefinition.parse(sys.stdin)
                self._update_metadata(input_definition.metadata)
                self.do_run(input_definition.inputs)
                return 0
            except Exception as e:
                logging.critical('Modular input: %s exit with exception: %s.',
                                 self.app, traceback.format_exc(e))
                return 1

        elif str(sys.argv[1]).lower() == '--scheme':
            sys.stdout.write(ET.tostring(self._scheme.to_xml()))
            sys.stdout.flush()
            return 0

        elif sys.argv[1].lower() == '--validate-arguments':
            try:
                validation_definition = ValidationDefinition.parse(sys.stdin)
                self._update_metadata(validation_definition.metadata)
                self.do_validation(validation_definition.parameters)
                return 0
            except Exception as e:
                logging.critical('Modular input: %s validate arguments with exception: %s.',
                                 self.app, traceback.format_exc(e))
                root = ET.Element('error')
                ET.SubElement(root, 'message').text = str(e)
                sys.stdout.write(ET.tostring(root))
                sys.stdout.flush
                return 1
        else:
            logging.critical('Modular input: %s run with invalid arguments: \"%s\".',
                             self.app, ' '.join(sys.argv))
            return 1
