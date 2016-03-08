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
log utility for Splunk solutions.
'''

import os
import logging
import logging.handlers as handlers
import os.path as op


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


class _Singleton(type):
    '''
    Singleton meta class
    '''

    def __init__(cls, name, bases, attrs):
        super(_Singleton, cls).__init__(name, bases, attrs)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instance


class Logs(object):
    '''A singleton class that manage all kinds of logger.

    All loggers created by this singleton class with different name
    and will be written to `log_dir`.

    :param default_level: (optional) Default logging level, default value
        is logging.INFO.

    Usage::

      >>> from splunksolutionlib.common import log
      >>> logger = log.Logs().get_logger('mymodule')
      >>> Logs.set_level(logging.DEBUG)
      >>> logger.debug('a debug log')
    '''

    __metaclass__ = _Singleton

    def __init__(self, default_level=logging.INFO):
        self._default_level = default_level
        self._loggers = {}

    def get_logger(self, name, directory=None, namespace=None,
                   level=None, max_bytes=25000000, backup_count=5):
        ''' Get logger with the name of `name`.

        If logger with the name of `name` exists just return else create a new
        logger with the name of `name`.

        :param name: Logger name, it will be used as log file name too.
        :type name: ``string``
        :param directory: (optional) Logger directory to write. If `log_dir` is
            None, log will be written to current directory.
        :type log_dir: ``string``
        :param namespace: (optional) Logger namespace.
        :type namespace: ``string``
        :param level: (optional) The logging level.
        :type level: ``(logging.DEBUG, logging.INFO, logging.ERROR)``
        :param max_bytes: (optional) The maximum log file size before rollover.
        :type max_bytes: ``integer``
        :param backup_count: (optional) The number of log files to retain.
        :type backup_count: ``integer``
        :returns: Instance of logging.Logger.
        :rtype: ``logging.Logger``
        '''

        logfile = self._get_logfile(name, directory, namespace)
        if logfile in self._loggers:
            return self._loggers[logfile]

        logger = logging.getLogger(logfile)
        handler_exists = any(
            [True for h in logger.handlers if h.baseFilename == logfile])
        if not handler_exists:
            file_handler = handlers.RotatingFileHandler(
                logfile,
                mode='a',
                maxBytes=max_bytes,
                backupCount=backup_count)
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s '
                'file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.setLevel(level or self._default_level)
            logger.propagate = False

        self._loggers[logfile] = logger
        return logger

    def set_level(self, level, name=None, directory=None, namespace=None):
        '''Set log level of logger.

        Set log level of all logger if `name` is None else of
        logger with the name of `name`.

        :param level: Log level to set.
        :param name: (optional) The name of logger.
        :type name: ``string``
        :param directory: (optional) Logger directory.
        :type log_dir: ``string``
        :param namespace: (optional) Logger namespace.
        :type namespace: ``string``
        '''

        if name:
            logfile = self._get_logfile(name, directory, namespace)
            logger = self._loggers.get(logfile)
            if logger:
                logger.setLevel(level)
        else:
            self._default_level = level
            for logger in self._loggers.itervalues():
                logger.setLevel(level)

    def _get_logfile(self, name, directory=None, namespace=None):
        if namespace:
            name = '{}_{}.log'.format(namespace, name)
        else:
            name = '{}.log'.format(name)

        directory = op.abspath(directory or os.curdir)
        logfile = op.sep.join([directory, name])

        return logfile
