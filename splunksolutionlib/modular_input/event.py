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

    @property
    def data(self):
        return self._data

    @property
    def time(self):
        return self._time

    @property
    def index(self):
        return self._index

    @property
    def host(self):
        return self._host

    @property
    def source(self):
        return self._source

    @property
    def sourcetype(self):
        return self._sourcetype

    @property
    def stanza(self):
        return self._stanza

    @property
    def unbroken(self):
        return self._unbroken

    @property
    def done(self):
        return self._done

    def __str__(self):
        event = {}
        event['data'] = self._data
        event['time'] = float(self._time) if self._time else self._time
        event['index'] = self._index
        event['host'] = self._host
        event['source'] = self._source
        event['sourcetype'] = self._sourcetype
        event['stanza'] = self._stanza
        event['unbroken'] = self._unbroken
        event['done'] = self._done

        return json.dumps(event)
