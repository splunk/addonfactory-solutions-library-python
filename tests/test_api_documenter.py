import sys
import os.path as op
from mock import Mock
sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
sys.modules['splunk'] = Mock()
sys.modules['splunk.rest'] = Mock()
from solnlib.api_documenter import *
import pytest


class TestApiDocumenter(object):
	@api()
	def test_init(self, *args, **kwargs):
		assert True

	@api_operation('get', 'Retrieving all records', 'get_all')
	@api_response(200, 'test', True)
	def test_handle_GET(self):
		assert True

	@api_operation('put', 'Creating new Record', 'create')
	@api_body_param(False, 'test')
	@api_model(False, ['name'], 'test', {'name': {'type': 'string'}})
	@api_response(200)
	def test_handle_PUT(self):
		assert True

	@api_operation('post', 'Updating single record by id', 'update')
	@api_body_param(False, 'test')
	@api_path_param()
	@api_response(200, 'test')
	def test_handle_POST(self):
		assert True

	@api_operation('delete', 'Deleting single record by id')
	@api_path_param()
	@api_response(200)
	def test_handle_DELETE(self):
		assert True


