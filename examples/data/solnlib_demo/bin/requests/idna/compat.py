# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

from .core import *
from .codec import *

def ToASCII(label):
    return encode(label)

def ToUnicode(label):
    return decode(label)

def nameprep(s):
    raise NotImplementedError("IDNA 2008 does not utilise nameprep protocol")

