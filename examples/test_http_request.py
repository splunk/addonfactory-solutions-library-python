import sys
import os.path as op

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib import http_request
from splunksolutionlib.credentials import get_session_key
import context


def test_http_request():
    session_key = get_session_key(
        context.username, context.password, scheme=context.scheme,
        host=context.host, port=context.port)

    hq = http_request.HTTPRequest(session_key, context.app, owner=context.owner,
                                  scheme=context.scheme, host=context.host,
                                  port=context.port, realm='splunksolutionlib',
                                  api_user='admin', timeout=20)

    url = '{scheme}://{host}:{port}/servicesNS/{owner}/{app}/storage/collections/config/sessions/acl?output_mode=json'
    content = hq.send(url.format(scheme=context.scheme, host=context.host,
                                 port=context.port, owner=context.owner,
                                 app=context.app))
    assert content
