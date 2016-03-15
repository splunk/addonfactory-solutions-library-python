from splunklib import binding
from splunklib.data import record

SESSION_KEY = 'nU1aB6BntzwREOnGowa7pN6avV3B6JefliAZIzCX9'


class _MocBufReader(object):
    def __init__(self, buf):
        self._buf = buf

    def read(self, size=None):
        return self._buf


def make_response_record(body, status=200):
    return record(
        {'body': binding.ResponseReader(_MocBufReader(body)),
         'status': status,
         'reason': None,
         'headers': None})
