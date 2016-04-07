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

from splunklib import binding

from splunksolutionlib.modular_input.event import XMLEvent, HECEvent

__all__ = ['ClassicEventWriter',
           'HECEventWriter']


class EventWriter(object):
    '''Base class of event writer.
    '''

    __metaclass__ = ABCMeta

    description = 'EventWriter'

    def close(self):
        '''Close event writer.
        '''

        pass

    @abstractmethod
    def create_event(self, data, time=None, index=None, host=None, source=None,
                     sourcetype=None, stanza=None, unbroken=False, done=False):
        '''Create a new event.

        :param data: Event data.
        :type data: ``json object``
        :param time: (optional) Event timestamp, default is None.
        :type time: ``float``
        :param index: (optional) The index event will be written to, default
            is None
        :type index: ``string``
        :param host: (optional) Event host, default is None.
        :type host: ``string``
        :param source: (optional) Event source, default is None.
        :type source: ``string``
        :param sourcetype: (optional) Event sourcetype, default is None.
        :type sourcetype: ``string``
        :param stanza: (optional) Event stanza name, default is None.
        :type stanza: ``string``
        :param unbroken: (optional) Event unbroken flag, default is False.
        :type unbroken: ``bool``
        :param done: (optional) The last unbroken event, default is False.
        :returns: ``bool``
        :returns: A new event object.
        :rtype: ``(XMLEvent, HECEvent)``

        Usage::
           >>> ew = event_writer.HECEventWriter(...)
           >>> event = ew.create_event(
           >>>     data='This is a test data.',
           >>>     time='%.3f' % 1372274622.493,
           >>>     index='main',
           >>>     host='localhost',
           >>>     source='Splunk',
           >>>     sourcetype='misc',
           >>>     stanza='test_scheme://test',
           >>>     unbroken=True,
           >>>     done=True)
        '''

        pass

    @abstractmethod
    def write_events(self, events):
        '''Write events.

        :param events: List of events to write.
        :type events: ``list``

        Usage::
           >>> from splunksolutionlib.modular_input import event_writer
           >>> ew = event_writer.EventWriter(...)
           >>> ew.write_events([event1, event2])
        '''

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

    def __init__(self):
        self._events_queue = Queue.Queue(10)
        self._events_writer = threading.Thread(target=self._write_events)
        self._events_writer.start()
        self._closed = False

    def close(self):
        self._closed = True
        self._events_queue.put(None)
        self._events_writer.join()

    def create_event(self, data, time=None, index=None, host=None, source=None,
                     sourcetype=None, stanza=None, unbroken=False, done=False):
        '''Create a new XMLEvent object.
        '''

        return XMLEvent(
            data, time=time, index=index, host=host, source=source,
            sourcetype=sourcetype, stanza=stanza, unbroken=unbroken, done=done)

    def write_events(self, events):
        if not events:
            return

        if self._closed:
            logging.error('Event writer: %s has been closed.', self.NAME)
            return

        for _event in XMLEvent.format_events(events):
            self._events_queue.put(_event)

    def _write_events(self):
        while 1:
            _event = self._events_queue.get()
            if _event is None:
                break
            logging.info('stream: %s', _event)
            sys.stdout.write(_event)
            sys.stdout.flush()


class HECEventWriter(EventWriter):
    '''Classic event writer.

    Use Splunk HEC as the output.

    :param token_name: Splunk HEC token name.
    :type token_name: ``string``
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
        >>> ew = event_writer.HECEventWriter(token_name, session_key)
        >>> ew.write_events([event1, event2])
        >>> ew.close()
    '''

    WRITE_EVENT_RETRIES = 3
    HTTP_INPUT_CONFIG_ENDPOINT = '/services/data/inputs/http'
    HTTP_EVENT_COLLECTOR_ENDPOINT = '/services/collector'

    description = 'HECEventWriter'

    def __init__(self, token_name, session_key,
                 scheme='https', host='localhost', port=8089):
        super(HECEventWriter, self).__init__()
        hec_port, hec_token = self._get_hec_config(
            token_name, session_key, scheme=scheme, host=host, port=port)
        self._context = binding.Context(
            scheme=scheme, host=host, port=hec_port, token=hec_token, autologin=True)

    def _get_hec_config(self, token_name, session_key, scheme, host, port):
        context = binding.Context(
            scheme=scheme, host=host, port=port, token=session_key, autologin=True)
        content = context.get(op.join(self.HTTP_INPUT_CONFIG_ENDPOINT, 'http'),
                              output_mode='json').body.read()
        port = int(json.loads(content)['entry'][0]['content']['port'])

        try:
            content = context.get(
                op.join(self.HTTP_INPUT_CONFIG_ENDPOINT, token_name),
                output_mode='json').body.read()
            token = json.loads(content)['entry'][0]['content']['token']
        except binding.HTTPError:
            content = context.post(self.HTTP_INPUT_CONFIG_ENDPOINT,
                                   name=token_name,
                                   output_mode='json').body.read()
            token = json.loads(content)['entry'][0]['content']['token']

        return (port, token)

    def create_event(self, data, time=None, index=None, host=None, source=None,
                     sourcetype=None, stanza=None, unbroken=False, done=False):
        '''Create a new HECEvent object.
        '''

        return HECEvent(
            data, time=time, index=index, host=host, source=source, sourcetype=sourcetype)

    def write_events(self, events):
        if not events:
            return

        for _event in HECEvent.format_events(events):
            retries = self.WRITE_EVENT_RETRIES
            while retries:
                try:
                    self._context.post(
                        self.HTTP_EVENT_COLLECTOR_ENDPOINT, body=_event,
                        headers=[('Content-Type', 'application/json')])
                    break
                except binding.HTTPError as e:
                    logging.error('Failed to write events through HEC: %s.',
                                  traceback.format_exc(e))
                    time.sleep(1)
                    retries -= 1
