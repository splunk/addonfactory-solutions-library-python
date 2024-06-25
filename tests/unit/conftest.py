import sys
from unittest.mock import MagicMock

# mock modules of 'splunk' library added 'splunk_rest_client'
sys.modules["splunk"] = MagicMock()
sys.modules["splunk.rest"] = MagicMock()
