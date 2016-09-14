import yaml
import os
import os.path as op
import sys
import inspect
import logging
import splunk.rest as rest
import log
import tempfile
import json

logger = log.Logs().get_logger('swagger')
logger.setLevel(logging.WARNING)


"""

Module for generating splunk custom rest endpoint api documentation
Currently this module uses swagger (http://swagger.io/) to generate the api documentation.
Users should add the decorators to the api methods to generate the documentation.
"""

"""
Note:
Whenever placing decorators over and operation, you must have an @api_operation on top
and an @api_response operation on the bottom. You can stack multiple
sets of the on top of each other each with different combinations of parameters.
The @api_model can be placed anywhere on this stack, unless you are using
model classes in which case it should be placed over each model class.
"""


def api_model(model_class, req=None, ref=None, obj=None):
	"""
	Creates a definition based on a model class.
	:param model_class: True if model class is being used, false otherwise. This parameter is required.
	:type: ```bool```
	:param req: A list of required variables. This parameter is optional if model_class is true.
	:type: ```list```
	:param ref: This is the name of the definition in the YAML spec. For example, #/definitions/ref.
			This parameter is optional if model_class is true.
	:type: ```basestring```
	:param obj: This is the model itself in the form of a dictionary. It is optional if model_class is True.
	:type: ```dict```
	"""
	def decorator(cls):
		if not spec.paths:
				return cls
		if model_class:
			params = vars(cls).items()
			definition = {}
			name = cls.__name__.replace("Model", "")
			fields = None
			# grab fields
			for param in params:
				if param[0] == '_field_list':
					fields = param[1]
			# create dictionary of definition to be added
			if fields:
				for field in fields:
					definition[field[0]] = field[1]
			spec.create_model(definition, name, req)
		else:
			definition = {'type': 'object', 'required': req, 'properties': obj}
			spec.add_definition(ref, definition)
		generator.write_temp()
		return cls
	return decorator


def api_operation(method, description=None, action=None):
	"""
	Documents the operation.
	:param method: The name of the operation. Valid values include get, put, post or delete.
	:type: ```basestring```
	:param description: (optional) A description of the operation.
	:type: ```basestring`````
	:param action: (optional)  The specific name of the operation, for example get_all.
	:type: ```basestring```
	"""
	def decorator(fn):
		def operation(*args, **kwargs):
			if not spec.paths:
				return fn(None, method, None, *args, **kwargs)
			op = {}
			tag = spec.get_path().replace("/", "")
			op['tags'] = [tag]
			if description:
				op['description'] = description
			if action:
				op['operationId'] = action
			# create empty list for parameters
			op['parameters'] = []
			return fn(spec.get_path(), method, op, *args, **kwargs)
		return operation
	return decorator


def path_param():
	"""
	Documents the path parameter
	"""
	def decorator(fn):
		def wrapper(path, name, op, *args, **kwargs):
			if not spec.paths:
				return fn(path, name, op, *args, **kwargs)
			path = path + "/{id}"
			# add path if it doesn't already exist
			if path not in spec.paths:
				spec.add_path(path)
			param = {
				"name": "id",
				"in": "path",
				"required": True,
				"type": "string"
			}
			op['parameters'].append(param)
			return fn(path, name, op, *args, **kwargs)
		return wrapper
	return decorator


def body_param(model_class, ref, is_list=False):
	"""
	Documents the body parameter.
	:param model_class: True is model class is being used and false otherwise.
	:type: ```bool```
	:param ref: This is the name of the definition in the YAML spec. For example, #/definitions/ref.
	:type: ```basestring```
	:param is_list: True if the body parameter is in the form of a list or array. Defaults to false.
	:type: ```bool```
	"""
	def decorator(fn):
		def wrapper(path, name, op, *args, **kwargs):
			if not spec.paths:
				return fn(path, name, op, *args, **kwargs)
			param = {
				"name": "body",
				"in": "body",
				"required": True
			}
			if is_list:
				param['schema'] = {'type': 'array', 'items': {'$ref': '#/definitions/' + ref}}
			else:
				param['schema'] = {'$ref': '#/definitions/' + ref}
			# add parameter to operation
			op['parameters'].append(param)
			return fn(path, name, op, *args, **kwargs)
		return wrapper
	return decorator


def query_param(param_name, required, param_type):
	"""
	Documents the query parameter
	:param param_name: Name of the parameter.
	:type: ```basestring```
	:param required: True if this param is required.
	:type: ```bool```
	:param param_type: The type of the parameter.
	:type: ```bool```
	"""
	def decorator(fn):
		def wrapper(path, name, op, *args, **kwargs):
			if not spec.paths:
				return fn(path, name, op, *args, **kwargs)
			param = {
				"name": param_name,
				"in": "query",
				"required": required,
				"type": param_type
			}
			# add parameter to operation
			op['parameters'].append(param)
			return fn(path, name, op, *args, **kwargs)
		return wrapper
	return decorator


def api_response(code, ref=None, is_list=None):
	"""
	Document the response for an operation.
	:param code: The api response code ie. 200, 400.
	:type: ```int```
	:param ref: (optional) This is the name of the definition in the YAML spec. For example, #/definitions/ref.
	:type: ```basestring```
	:param is_list: (optional) True if the body parameter is in the form of a list or array. Defaults to false.
	:type: ```bool```
	"""
	def decorator(fn):
		def wrapper(path, name, op, *args, **kwargs):
			if not spec.paths:
				if fn.__name__ == 'wrapper':
					return fn(path, name, op, *args, **kwargs)
				else:
					return fn(*args, **kwargs)
			# response code map
			code_map = {
				200: 'OK',
				201: 'Created',
				202: 'Accepted',
				400: 'Bad Request',
				401: 'Unauthorized',
				403: 'Forbidden',
				404: 'Not Found'
			}
			# begin making response object
			response = {code: {'description':code_map[code]}}
			if ref:
				if is_list:
					response[code]['schema'] = {'type': 'array', 'items': {'$ref': '#/definitions/' + ref}}
				else:
					response[code]['schema'] = {'$ref': '#/definitions/' + ref}
			if 'responses' not in op:
				op['responses'] = response
			else:
				op['responses'][code] = response[code]
			if fn.__name__ == 'wrapper':
				return fn(path, name, op, *args, **kwargs)
			elif fn.__name__ == 'operation':
				spec.add_operation(path, name, op)
				generator.write_temp()
				return fn(*args, **kwargs)
			else:
				spec.add_operation(path, name, op)
				generator.write_temp()
				return fn(*args, **kwargs)
		return wrapper
	return decorator


def api():
	"""
	Sets the info and paths for the specification.
	This must be place above the rest.BaseRestHandler subclass's __init__ function.
	"""
	def decorator(fn):
		def wrapper(*args, **kwargs):
			# only write spec if it is asked for
			if 'spec' not in args[2]['query']:
				fn(*args, **kwargs)
				return
			path_keys = ['', 'services', 'app', 'version', 'api', 'id', 'action']
			path_params = dict(zip(path_keys, args[2]['path'].split('/')))
			app = path_params.get('app')
			version = path_params.get('version')
			api_name = path_params.get('api')
			spec.set_version(version)
			spec.set_title(app)
			host_url = args[2]['headers']['x-request-url']
			base_host_url = host_url.split('/services/')[0]
			url = base_host_url.split('://')
			spec.set_schemes(url[0])
			spec.set_host(url[1] + "/services/" + app + "/" + version)
			spec.add_path("/" + api_name)
			generator.write_temp()
			fn(*args, **kwargs)
			return
		return wrapper
	return decorator


def get_spec(context, method_list):
	"""
	Generates and Returns the spec file data
	:param context: Dictionary with app, session, version and api fields
	:type: ```dict```
	:param method_list: List of API methods to call
	:type: ```list```
	:return: generated spec file
	:rtype: ```basestring```
	"""
	_generate_documentation(context, method_list)
	with open(tempfile.gettempdir() + op.sep + 'spec.yaml') as stream:
		try:
			spec_file = yaml.load(stream)
		except yaml.YAMLError as ex:
			raise ex
		return json.dumps(spec_file)


def _update_spec():
	"""
	Update specification
	"""
	generator.update_spec()


def _generate_documentation(context, method_list):
	"""
	Generates documentation spec file by calling api methods
	:param context: Dict with app, session, version and api fields
	:param method_list: List of API methods to call
	"""
	uri = '{}/{}/{}'.format(context.get('app'), context.get('version'), context.get('api'))
	for method in method_list:
		rest.simpleRequest(uri, context.get('session'), None, None, method)
	_update_spec()


class _SwaggerSpecGenerator(object):
	"""
	Private class to generate the swagger spec file.
	"""
	def __init__(self, swagger_api):
		self.api = swagger_api
		self.order = ["swagger", "info", "host", "schemes", "consumes", "produces", "paths", "definitions"]

	def write_temp(self):
		"""
		Stores changes to the spec in a temp file.
		"""
		spec = {
				"swagger": self.api.get_swagger(),
				"info": self.api.get_info(),
				"host": self.api.get_host(),
				"schemes": self.api.get_schemes(),
				"consumes": self.api.get_consumes(),
				"produces": self.api.get_produces(),
				"paths": self.api.get_paths(),
				"definitions": self.api.get_definitions()
				}

		stream = file((tempfile.gettempdir() + op.sep + 'temp.yaml'), 'w')
		for x in self.order:
			yaml.dump({x: spec[x]}, stream, default_flow_style=False)

	def update_spec(self):
		"""
		Updates the specification from the temp file.
		"""
		os.rename(tempfile.gettempdir() + op.sep + 'temp.yaml', tempfile.gettempdir() + op.sep + 'spec.yaml')


class _SwaggerApi(object):
	"""
	Private class to generate the swagger documentation and default params values.
	"""
	def __init__(self):
		if op.isfile(tempfile.gettempdir() + op.sep + 'temp.yaml'):
			with open(tempfile.gettempdir() + op.sep + 'temp.yaml', "r") as stream:
				try:
					spec = yaml.load(stream)
					self.swagger = spec["swagger"]
					self.info = spec["info"]
					self.host = spec["host"]
					self.schemes = spec["schemes"]
					self.consumes = spec["consumes"]
					self.produces = spec["produces"]
					self.paths = spec["paths"]
					self.definitions = spec["definitions"]
				except yaml.YAMLError as e:
					raise e
		else:
			self.swagger = "2.0"
			self.info = {
				"description": "A Splunk REST API"
			}
			self.host = None
			self.schemes = ["http"]
			self.consumes = ["application/json"]
			self.produces = ["application/json"]
			self.paths = {}
			self.definitions = {}
		self.type_converter = {
			"BooleanType": "boolean",
			"CustomStringType": "string",
			"IntType": "integer",
			"FloatType": "float",
			"DictType": "object",
			"LongType": "long",
			"DateTimeType": "dateTime"
		}
		self.default_dict = {
			'integer': 0,
			'float': 0.0,
			'double': 0.0,
			'string': '',
			'binary': '0b',
			'boolean': False,
			'long': 0L,
			'dateTime': 0.0,
			'byte': 'dGVzdGluZyBkYXRhIDENCnRlc3RpbmcgZGF0YSAy'
		}
		self.swagger_types = {
			"integer": "integer",
			"long": "integer",
			"float": "number",
			"double": "number",
			"string": "string",
			"binary": "string",
			"dateTime": "string",
			"boolean": "boolean",
			"byte": "string"
		}

	def get_info(self):
		return self.info

	def get_swagger(self):
		return self.swagger

	def get_host(self):
		return self.host

	def get_schemes(self):
		return self.schemes

	def get_consumes(self):
		return self.consumes

	def get_produces(self):
		return self.produces

	def get_paths(self):
		return self.paths

	def get_definitions(self):
		return self.definitions

	def get_path(self):
		name = self.paths.keys()[0].split("/")[1]
		return "/" + name

	def set_title(self, title):
		self.info['title'] = title

	def set_version(self, version):
		self.info['version'] = version

	def set_host(self, host):
		self.host = host

	def set_schemes(self, scheme):
		self.schemes = [scheme]

	def add_operation(self, path, name, op):
		"""
		Add a new operation to the api spec.
		"""
		self.paths[path][name] = op

	def add_path(self, path):
		"""
		Add a new path to the api spec.
		"""
		if path not in self.paths:
			self.paths[path] = {}

	def add_definition(self, name, definition):
		"""
		Add a new definition to the api spec.
		"""
		self.add_examples(definition['properties'])
		self.fix_types(definition['properties'])
		self.definitions[name] = definition

	def create_model(self, params, name, req):
		"""
		Create a model to be added to the definitions of the spec.
		"""
		# convert given dict to a formatted one
		definition = {"properties": {}}
		# add requirements if given
		if req:
			definition["requirements"] = req
		for param in params:
			# get type of property
			info = str(params.get(param)).split(" ")
			type_info = info[0].replace("<", "")
			prop_type = type_info[:type_info.index('(')]
			if prop_type in self.type_converter:
				definition["properties"][param] = {"type": self.type_converter[prop_type]}
			# check for array
			elif prop_type == 'ListType':
				items = type_info[type_info.index('(') + 1: type_info.index(')')]
				if items != 'ModelType':
					definition["properties"][param] = {"type": 'array'}
					definition["properties"][param]['items'] = {'type': self.type_converter[items]}
			else:
				start, end = type_info.index("(") + 1, type_info.index(")")
				ref = type_info[start:end].replace("Model", "")
				definition["properties"][param] = {"$ref": ref}
		self.add_definition(name, definition)

	def add_examples(self, properties):
		"""
		Add examples to documentation for a definition
		"""
		for prop in properties:
			if 'type' in properties[prop] and properties[prop]['type'] in self.default_dict\
					and 'example' not in properties[prop]:
				properties[prop]['example'] = self.default_dict[properties[prop]['type']]

	def fix_types(self, properties):
		"""
		Fix types to make the spec Open API compliant.
		"""
		for prop in properties:
			if 'type' in properties[prop] and properties[prop]['type'] in self.swagger_types:
				if properties[prop]['type'] != self.swagger_types[properties[prop]['type']]:
					properties[prop]['format'] = properties[prop]['type']
					properties[prop]['type'] = self.swagger_types[properties[prop]['type']]
			if '$ref' in properties[prop]:
				properties[prop]['$ref'] = '#/definitions/' + properties[prop]['$ref']

spec = _SwaggerApi()
generator = _SwaggerSpecGenerator(spec)
