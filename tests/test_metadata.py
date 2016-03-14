import sys
import os.path as op
import unittest as ut

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import splunkenv


def mock_make_splunkhome_path(parts):
    cur_dir = op.dirname(op.abspath(__file__))

    return op.sep.join([cur_dir, 'data/local.meta'])


class TestGetSplunkdUri(ut.TestCase):
    def setUp(self):
        self._make_splunkhome_path_backup = splunkenv.make_splunkhome_path
        splunkenv.make_splunkhome_path = mock_make_splunkhome_path

    def tearDown(self):
        splunkenv.make_splunkhome_path = self._make_splunkhome_path_backup

    def test_metadata_reader(self):
        from splunksolutionlib import metadata

        mr = metadata.MetadataReader('Splunk_TA_test')

        self.assertEqual(mr.get('conf1', 'stanza1', 'modtime'),
                         '1453272423.443622000')

        self.assertEqual(mr.get_float('conf1', 'stanza1', 'modtime'),
                         1453272423.443622000)

        with self.assertRaises(ValueError):
            mr.get('conf_bad', 'stanza1', 'modtime')

        with self.assertRaises(ValueError):
            mr.get('conf_bad', 'stanza_bad', 'modtime')

        with self.assertRaises(ValueError):
            mr.get_float('conf_bad', 'stanza1', 'version')

if __name__ == '__main__':
    ut.main(verbosity=2)
