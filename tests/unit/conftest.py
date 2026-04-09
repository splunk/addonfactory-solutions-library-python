import json
import socket
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest


@pytest.fixture(scope="session")
def http_mock_server():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = s.getsockname()[1]

    class Mock:
        def __init__(self, host, port):
            self.host = host
            self.port = port
            self.get_func = None

        def get(self, func):
            self.get_func = func
            return func

    mock = Mock("localhost", port)

    class RequestArg:
        def __init__(self):
            self.headers = {
                "Content-Type": "application/json",
            }
            self.response_code = 200

        def send_header(self, key, value):
            self.headers[key] = value

        def send_response(self, code):
            self.response_code = code

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if mock.get_func is None:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))
                return

            request = RequestArg()
            response = mock.get_func(request)

            self.send_response(request.response_code)

            for key, value in request.headers.items():
                self.send_header(key, value)

            self.end_headers()

            if isinstance(response, dict):
                response = json.dumps(response)

            self.wfile.write(response.encode("utf-8"))

    server_address = ("", mock.port)
    httpd = HTTPServer(server_address, Handler)

    thread = Thread(target=httpd.serve_forever)
    thread.setDaemon(True)
    thread.start()

    yield mock

    httpd.shutdown()
    httpd.server_close()
    thread.join()
