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
import time
import json
import threading
import logging
import traceback
import Queue
import os.path as op
from abc import ABCMeta, abstractmethod
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from splunklib import binding

__all__ = ['ClassicEventWriter',
           'HECEventWriter']


class EventWriter(object):
    __metaclass__ = ABCMeta

    description = 'EventWriter'

    def __init__(self):
        self._events_queue = Queue.Queue(1000)
        self._events_writer = threading.Thread(target=self._write_events)
        self._events_writer.start()
        self._closed = False

    def write_events(self, events):
        if self._closed:
            logging.error('Event writer: %s has been closed.', self.NAME)
            return

        for event in self._format_events(events):
            self._events_queue.put(event)

    def close(self):
        self._closed = True
        self._events_queue.put(None)
        self._events_writer.join()

    @abstractmethod
    def _format_events(self, events):
        pass

    @abstractmethod
    def _write_events(self):
        pass


class ClassicEventWriter(EventWriter):
    description = 'ClassicEventWriter'

    def _format_events(self, events):
        stream = ET.Element("stream")
        for event in events:
            stream.append(event.to_xml())

        return [ET.tostring(stream)]

    def _write_events(self):
        while 1:
            event = self._events_queue.get()
            if event is None:
                break

            sys.stdout.write(event)
            sys.stdout.flush()


class HECEventWriter(EventWriter):
    WRITE_RETRIES = 3
    MAX_HEC_EVENT_LENGTH = 100000
    HTTP_INPUT_TOKEN_NAME = 'splunksolutionlib_token'
    HTTP_INPUT_CONFIG_ENDPOINT = '/services/data/inputs/http'
    HTTP_EVENT_COLLECTOR_ENDPOINT = '/services/collector'

    description = 'HECEventWriter'

    def __init__(self, session_key,
                 scheme='https', host='localhost', port=8089):
        super(HECEventWriter, self).__init__()
        hec_port, hec_token = self._get_hec_config(
            session_key, scheme=scheme, host=host, port=port)
        self._context = binding.Context(
            scheme=scheme, host=host, port=hec_port, token=hec_token, autologin=True)

    def _get_hec_config(self, session_key,
                        scheme='https', host='localhost', port=8089):
        context = binding.Context(
            scheme=scheme, host=host, port=port, token=session_key, autologin=True)
        content = context.get(op.join(self.HTTP_INPUT_CONFIG_ENDPOINT, 'http'),
                              output_mode='json').body.read()
        port = int(json.loads(content)['entry'][0]['content']['port'])

        try:
            content = context.get(
                op.join(self.HTTP_INPUT_CONFIG_ENDPOINT, self.HTTP_INPUT_TOKEN_NAME),
                output_mode='json').body.read()
            token = json.loads(content)['entry'][0]['content']['token']
        except binding.HTTPError:
            content = context.post(self.HTTP_INPUT_CONFIG_ENDPOINT,
                                   name=self.HTTP_INPUT_TOKEN_NAME,
                                   output_mode='json').body.read()
            token = json.loads(content)['entry'][0]['content']['token']

        return (port, token)

    def _format_events(self, events):
        events = [event.to_json() for event in events]

        size = 0
        new_events, batched_events = [], []
        for event in events:
            new_length = size + len(event) + len(batched_events) - 1
            if new_length >= self.MAX_HEC_EVENT_LENGTH:
                new_events.append("\n".join(batched_events))
                del batched_events[:]
                size = 0
            batched_events.append(event)
            size = size + len(event)
        if len(batched_events):
            new_events.append("\n".join(batched_events))
        return new_events

    def _write_events(self):
        while 1:
            event = self._events_queue.get()
            if event is None:
                break

            retries = self.WRITE_RETRIES
            while retries:
                try:
                    self._context.post(
                        self.HTTP_EVENT_COLLECTOR_ENDPOINT, body=event,
                        headers=[('Content-Type', 'application/json')])
                    break
                except binding.HTTPError as e:
                    logging.error('Failed to write events through HEC: %s.',
                                  traceback.format_exc(e))
                    time.sleep(1)
                    retries -= 1
