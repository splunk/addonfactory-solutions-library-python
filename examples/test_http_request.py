import sys
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import http_request
import context


def test_http_request():
    hq = http_request.HTTPRequest(
        api_user=context.username, api_password=context.password, timeout=20)

    url = '{scheme}://{host}:{port}/services/data/inputs/http'
    content = hq.send(url.format(
        scheme=context.scheme, host=context.host, port=context.port))
    assert content
