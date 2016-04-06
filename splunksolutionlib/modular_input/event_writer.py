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

'''
This module provides two kinds of event writers (ClassicEventWriter,
HECEventWriter) to write Splunk modular input events.
'''

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
    '''Base class of event writer.
    '''

    __metaclass__ = ABCMeta

    description = 'EventWriter'

    def __init__(self):
        self._events_queue = Queue.Queue(1000)
        self._events_writer = threading.Thread(target=self._write_events)
        self._events_writer.start()
        self._closed = False

    def write_events(self, events):
        '''Write events.

        :param events: List of events to write.
        :type events: ``list``

        Usage::
           >>> from splunksolutionlib.modular_input import event_writer
           >>> ew = event_writer.EventWriter(...)
           >>> ew.write_events([event1, event2])
        '''

        if self._closed:
            logging.error('Event writer: %s has been closed.', self.NAME)
            return

        for event in self._format_events(events):
            self._events_queue.put(event)

    def close(self):
        '''Close event writer.
        '''

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
    '''Classic event writer.

    Use sys.stdout as the output.

    Usage::
        >>> from splunksolutionlib.modular_input import event_writer
        >>> ew = event_writer.ClassicEventWriter()
        >>> ew.write_events([event1, event2])
        >>> ew.close()
    '''

    description = 'ClassicEventWriter'

    def _event_to_xml(self, event):
        _event = ET.Element('event')
        if event.stanza:
            _event.set('stanza', event.stanza)
        if event.unbroken:
            _event.set('unbroken', str(int(event.unbroken)))

        if event.time:
            ET.SubElement(_event, 'time').text = event.time

        sub_elements = [('index', event.index),
                        ('host', event.host),
                        ('source', event.source),
                        ('sourcetype', event.sourcetype)]
        for node, value in sub_elements:
            if value:
                ET.SubElement(_event, node).text = value

        if isinstance(event.data, (unicode, basestring)):
            ET.SubElement(_event, 'data').text = event.data
        else:
            ET.SubElement(_event, 'data').text = json.dumps(event.data)

        if event.done:
            ET.SubElement(_event, 'done')

        return _event

    def _format_events(self, events):
        '''Output:
               ['<stream>
                   <event stanza="test_scheme://test" unbroken="1">
                         <time>1459919070.994</time>
                         <index>main</index>
                         <host>localhost</host>
                         <source>test</source>
                         <sourcetype>test</sourcetype>
                         <data>{"kk": [1, 2, 3]}</data>
                     <done />
                   </event>
                   <event stanza="test_scheme://test" unbroken="1">
                         <time>1459919082.961</time>
                         <index>main</index>
                         <host>localhost</host>
                         <source>test</source>
                         <sourcetype>test</sourcetype>
                         <data>{"kk": [3, 2, 3]}</data>
                         <done />
                   </event>
                 </stream>',
             '...']
        '''

        stream = ET.Element("stream")
        for event in events:
            stream.append(self._event_to_xml(event))

        return [ET.tostring(stream)]

    def _write_events(self):
        while 1:
            event = self._events_queue.get()
            if event is None:
                break

            sys.stdout.write(event)
            sys.stdout.flush()


class HECEventWriter(EventWriter):
    '''Classic event writer.

    Use Splunk HEC as the output.

    :param session_key: Splunk access token.
    :type session_key: ``string``
    :param scheme: (optional) The access scheme, default is `https`.
    :type scheme: ``string``
    :param host: (optional) The host name, default is `localhost`.
    :type host: ``string``
    :param port: (optional) The port number, default is 8089.
    :type port: ``integer``

    Usage::
        >>> from splunksolutionlib.modular_input import event_writer
        >>> ew = event_writer.HECEventWriter(session_key)
        >>> ew.write_events([event1, event2])
        >>> ew.close()
    '''

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

    def _get_hec_config(self, session_key, scheme, host, port):
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

    def _event_to_str(self, event):
        _event = {}
        _event['event'] = event.data
        if event.time:
            _event['time'] = float(event.time)
        if event.index:
            _event['index'] = event.index
        if event.host:
            _event['host'] = event.host
        if event.source:
            _event['source'] = event.source
        if event.sourcetype:
            _event['sourcetype'] = event.sourcetype

        return json.dumps(_event)

    def _format_events(self, events):
        '''Output:
               ['{"index": "main", ... "event": {"kk": [1, 2, 3]}}\n'
                '{"index": "main", ... "event": {"kk": [3, 2, 3]}}',
                '...']
        '''
        events = [self._event_to_str(event) for event in events]

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
