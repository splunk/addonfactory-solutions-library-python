import sys
import os.path as op
import pytest

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import splunkenv


def _mock_make_splunkhome_path(parts):
    cur_dir = op.dirname(op.abspath(__file__))
    return op.sep.join([cur_dir, 'data/unittest/local.meta'])


class TestMetadataReader(object):

    def test_get(self, monkeypatch):
        monkeypatch.setattr(splunkenv, 'make_splunkhome_path',
                            _mock_make_splunkhome_path)

        from splunksolutionlib import metadata
        mr = metadata.MetadataReader('Splunk_TA_test')

        assert mr.get('conf1', 'stanza1', 'modtime') == '1453272423.443622000'

        assert mr.get_float('conf1', 'stanza1', 'modtime') == 1453272423.443622000

        with pytest.raises(ValueError):
            mr.get('conf_bad', 'stanza1', 'modtime')

        with pytest.raises(ValueError):
            mr.get('conf_bad', 'stanza_bad', 'modtime')

    def test_get_float(self, monkeypatch):
        monkeypatch.setattr(splunkenv, 'make_splunkhome_path',
                            _mock_make_splunkhome_path)

        from splunksolutionlib import metadata
        mr = metadata.MetadataReader('Splunk_TA_test')

        assert mr.get_float('conf1', 'stanza1', 'modtime') == 1453272423.443622000

        with pytest.raises(ValueError):
            mr.get_float('conf_bad', 'stanza1', 'version')
