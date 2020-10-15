#!/usr/bin/env python

# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-

"""
certifi.py
~~~~~~~~~~

This module returns the installation location of cacert.pem.
"""
import os


def where():
    f = os.path.dirname(__file__)

    return os.path.join(f, 'cacert.pem')


if __name__ == '__main__':
    print(where())
