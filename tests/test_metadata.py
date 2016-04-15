import sys
import os.path as op
import pytest

import common

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import metadata


class TestMetadataReader(object):

    def test_get(self, monkeypatch):
        common.mock_splunkhome(monkeypatch)

        mr = metadata.MetadataReader(common.app)

        assert mr.get('sessions', 'test', 'modtime') == '1453272423.443622000'
        with pytest.raises(ValueError):
            mr.get('conf_bad', 'stanza_bad', 'modtime')

    def test_get_float(self, monkeypatch):
        common.mock_splunkhome(monkeypatch)

        mr = metadata.MetadataReader('unittest')

        assert mr.get_float('sessions', 'test', 'modtime') == 1453272423.443622000
        with pytest.raises(ValueError):
            mr.get_float('sessions', 'test', 'version')
