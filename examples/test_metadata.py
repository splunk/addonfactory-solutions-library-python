import sys
import os.path as op
import six
sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import metadata
import context


def test_metadata_reader():
    mr = metadata.MetadataReader(context.app)

    modtime = mr.get('collections', 'sessions', 'modtime')
    assert isinstance(modtime, six.text_type)

    modtime = mr.get_float('collections', 'sessions', 'modtime')
    assert type(modtime) == float
