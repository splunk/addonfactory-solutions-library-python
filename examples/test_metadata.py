# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

import sys
import os.path as op
import six

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import metadata
import context

# This test requires sudo permission to access the file under $SPLUNK_HOME/etc/solnlib_demo/metadata/local.meta
def test_metadata_reader():
    mr = metadata.MetadataReader(context.app)

    modtime = mr.get("collections", "sessions", "modtime")
    assert isinstance(modtime, str)

    modtime = mr.get_float("collections", "sessions", "modtime")
    assert type(modtime) == float
