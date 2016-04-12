import sys
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.splunkenv import get_splunkd_access_info

owner = 'nobody'
app = 'splunksolutionlib_demo'

username = 'admin'
password = 'admin'

scheme, host, port = get_splunkd_access_info()
