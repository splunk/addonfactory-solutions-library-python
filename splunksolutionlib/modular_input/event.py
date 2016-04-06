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
This module provides Splunk modular input event encapsulation.
'''

import json
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

__all__ = ['Event']


class EventException(Exception):
    pass


class Event(object):
    def __init__(self, data, time=None, index=None, host=None, source=None,
                 sourcetype=None, stanza=None, unbroken=False, done=False):
        '''Modular input event.

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

        Usage::
           >>> event = Event(
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

        self._data = data
        self._time = '%.3f' % time if time else None
        self._index = index
        self._host = host
        self._source = source
        self._sourcetype = sourcetype
        self._stanza = stanza
        if not unbroken and done:
            raise EventException('Invalid combination of unbroken and done.')
        self._unbroken = unbroken
        self._done = done

    def to_xml(self):
        '''Get an xml representation of event.

        :returns: An xml object.
        :rtype: ``xml object``
        '''

        event = ET.Element('event')
        if self._stanza:
            event.set('stanza', self._stanza)
        if self._unbroken:
            event.set('unbroken', str(int(self._unbroken)))

        if self._time:
            ET.SubElement(event, 'time').text = self._time

        sub_elements = [('index', self._index),
                        ('host', self._host),
                        ('source', self._source),
                        ('sourcetype', self._sourcetype)]
        for node, value in sub_elements:
            if value:
                ET.SubElement(event, node).text = value

        if isinstance(self._data, (unicode, basestring)):
            ET.SubElement(event, 'data').text = self._data
        else:
            ET.SubElement(event, 'data').text = json.dumps(self._data)

        if self._done:
            ET.SubElement(event, 'done')

        return event

    def to_string(self):
        event = {}
        event['event'] = self._data
        if self._time:
            event['time'] = float(self._time)
        if self._index:
            event['index'] = self._index
        if self._host:
            event['host'] = self._host
        if self._source:
            event['source'] = self._source
        if self._sourcetype:
            event['sourcetype'] = self._sourcetype

        return json.dumps(event)
