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
This module provides log functionalities.
'''

import os
import logging
import logging.handlers as handlers
import os.path as op

from splunksolutionlib.common.pattern import Singleton

__all__ = ['log_enter_exit',
           'Logs']


def log_enter_exit(logger):
    '''Decorator for logger to log function enter and exit.

    This decorator will generate a lot of debug log, please add this
    only when it is required.

    :param logger: logger to decorate.

    Usage::
      >>> @log_enter_exit
      >>> def myfunc():
      >>>     doSomething()
    '''

    def log_decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug('%s entered', func.__name__)
            result = func(*args, **kwargs)
            logger.debug('%s exited', func.__name__)
            return result

        return wrapper

    return log_decorator


class Logs(object):
    '''A singleton class that manage all kinds of logger.

    Usage::

      >>> from splunksolutionlib.common import log
      >>> log.Logs.set_context(directory='/var/log/test',
                               namespace='test')
      >>> logger = log.Logs().get_logger('mymodule')
      >>> logger.set_level(logging.DEBUG)
      >>> logger.debug('a debug log')
    '''

    __metaclass__ = Singleton

    _default_directory = None
    _default_namespace = None
    _default_log_level = logging.INFO
    _default_max_bytes = 25000000
    _default_backup_count = 5

    def __init__(self):
        self._loggers = {}

    @classmethod
    def set_context(cls, **context):
        """set log context.

        :param directory: (optional) Logger directory to write. If `log_dir` is
            None, log will be written to current directory.
        :type log_dir: ``string``
        :param namespace: (optional) Logger namespace.
        :type namespace: ``string``
        :param default_level: (optional) Default logging level, default value
            is logging.INFO.
        :type default_level: ``integer``
        :param max_bytes: (optional) The maximum log file size before rollover.
        :type max_bytes: ``integer``
        :param backup_count: (optional) The number of log files to retain.
        :type backup_count: ``integer``
        """

        if 'directory' in context:
            cls._default_directory = context['directory']
        if 'namespace' in context:
            cls._default_namespace = context['namespace']
        if 'log_level' in context:
            cls._default_log_level = context['log_level']
        if 'max_bytes' in context:
            cls._default_max_bytes = context['max_bytes']
        if 'backup_count' in context:
            cls._default_backup_count = context['backup_count']

    def get_logger(self, name):
        ''' Get logger with the name of `name`.

        If logger with the name of `name` exists just return else create a new
        logger with the name of `name`.

        :param name: Logger name, it will be used as log file name too.
        :type name: ``string``
        :returns: Instance of logging.Logger.
        :rtype: ``logging.Logger``
        '''

        logfile = self._get_logfile(name)
        if logfile in self._loggers:
            return self._loggers[logfile]

        logger = logging.getLogger(logfile)
        handler_exists = any(
            [True for h in logger.handlers if h.baseFilename == logfile])
        if not handler_exists:
            file_handler = handlers.RotatingFileHandler(
                logfile,
                mode='a',
                maxBytes=self._default_max_bytes,
                backupCount=self._default_backup_count)
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s '
                'file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.setLevel(self._default_log_level)
            logger.propagate = False

        self._loggers[logfile] = logger
        return logger

    def set_level(self, level, name=None):
        '''Set log level of logger.

        Set log level of all logger if `name` is None else of
        logger with the name of `name`.

        :param level: Log level to set.
        :param name: (optional) The name of logger.
        :type name: ``string``
        '''

        if name:
            logfile = self._get_logfile(name)
            logger = self._loggers.get(logfile)
            if logger:
                logger.setLevel(level)
        else:
            self._default_log_level = level
            for logger in self._loggers.itervalues():
                logger.setLevel(level)

    def _get_logfile(self, name):
        if self._default_namespace:
            name = '{}_{}.log'.format(self._default_namespace, name)
        else:
            name = '{}.log'.format(name)

        directory = op.abspath(self._default_directory or os.curdir)
        logfile = op.sep.join([directory, name])

        return logfile
