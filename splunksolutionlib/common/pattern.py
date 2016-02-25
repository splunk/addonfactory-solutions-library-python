# -*- coding: utf-8 -*-

"""
Commonly used design partten for python user, includes:
  - singleton (Decorator function used to build singleton)

:copyright: (c) 2016 by Splunk, Inc.
"""


class Singleton(type):
    """
    Singleton meta class
    """

    def __init__(cls, name, bases, attrs):
        super(Singleton, cls).__init__(name, bases, attrs)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance
