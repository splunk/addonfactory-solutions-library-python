# Splunk Solution Library for Python Changelog

## Version 1.1.0

### New features and APIs

* Enhance splunk_rest_client APIs to support local splunkd access without passing
  scheme, host and port.
* Add http connection pooling switch to splunk_rest_client. By default the http connection pooling
  is not turned on, but for KVStore checkpointer and Http Event Writer, the http connection
  pooling is turned on

### Notes

* Rename `CredNotExistException` to `CredentialNotExistException`

## Version 1.0.1

### Bug fixes

* Fix dependency on Splunk SDK.

## Version 1.0.0

### New features and APIs

* Sphinx based library docs and improved source code docstrings.
* Improved unit and integration tests.
* Support new log utilities based on splunk context.
	- Added solnlib.log + units
* Support object ACL CRUD operations.
    - Added solnlib.acl + units
    - Added examples/test_acl.py
* Support orphan process monitor
	- Added solnlib.orphan_process_monitor + units
* Support zip file compression/decompression.
	- Added solnlib.compression + units
* Support configuration file management class, it can encrypt/decrypt specifiled fields of
  stanza automatically
  - Added solnlib.conf_manager + units
  - Added examples/test_conf_manager.py
* Support splunk credential CRUD operations.
  - Added solnlib.credentials + units
  - Added examples/test_credentials.py
* Support file monitor.
  - Added solnlib.file_monitor + units
* Support IP manipulate/calculation functionalities.
  - Added solnlib.ip_math + units
* Support configuration parser for Splunk local.metadata.
  - Added solnlib.metadata + units
  - Added examples/test_metadata.py
* Support Net utilities.
  - Added solnlib.net_utils + units
* Support utilities to get splunk server related info.
  - Added solnlib.server_info + units
  - Added examples/test_server_info.py
* Support rest client wrapper to enable http proxy and certification.
  - Added solnlib.splunk_rest_client + units
* Support environment utilities
  - Added solnlib.splunkenv + units
  - Added examples/test_splunkenv.py
* Support user access related utilities
  - Added solnlib.user_access + units
  - Added examples/test_user_access.py
