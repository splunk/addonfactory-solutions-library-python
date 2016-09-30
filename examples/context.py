import sys
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib.splunkenv import get_splunkd_access_info

owner = 'nobody'
app = 'solnlib_demo'

username = 'admin'
password = 'changeme'

scheme, host, port = get_splunkd_access_info()
