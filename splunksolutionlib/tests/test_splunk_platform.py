import os
import sys
import unittest as ut

sys.path.append("../")

from splunktalib import splunk_platform as sp


class TestGetSplunkdUri(ut.TestCase):

    # Testcase depends on SPLUNK_HOME env variables
    def test_splunkd_uri(self):
        uri = sp.get_splunkd_uri()
        self.assertEquals(uri, "https://127.0.0.1:8089")

        os.environ["SPLUNKD_URI"] = "https://10.0.0.1:8089"
        uri = sp.get_splunkd_uri()
        self.assertEquals(uri, "https://10.0.0.1:8089")

        del os.environ["SPLUNKD_URI"]
        os.environ["SPLUNK_BINDIP"] = "10.0.0.2:7080"
        uri = sp.get_splunkd_uri()
        self.assertEquals(uri, "https://10.0.0.2:8089")

        os.environ["SPLUNK_BINDIP"] = "10.0.0.3"
        uri = sp.get_splunkd_uri()
        self.assertEquals(uri, "https://10.0.0.3:8089")


if __name__ == "__main__":
    ut.main()
