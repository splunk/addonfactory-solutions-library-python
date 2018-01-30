# Splunk Solution Library for Python Changelog

## Version 1.0.17
* Security vulnerability fix APPSC-2406
 
## Version 1.0.16

### Bug fixes
* Change log level to `warning` for `retry` failure.
* Remove duplicated variable `checkpointer_name` in `ModularInput._create_checkpointer`.
* Fix concurrency conflict for encrypting and decrypting password.
* Cancel redundant `sleep` after last `retry` failed.
* Fix app name in returned conf file.
* Performance improvement for getting stanzas in app.

## Version 1.0.15

### New features
* Change the way dependencies are handled.
* Package all of solnlib's dependencies in its own packages folder.
* Changes import statements to use relative imports.
* Performance improvement for ClassicEventWriter
* Simplify HECEventWriter creation with options
* Add licenses for all packaged dependencies

## Version 1.0.14

### New features
* Rest api documenter with swagger standard

### Bug fixes

* Credentials are no longer stored when the stanza doesn't contain encrypted fields

## Version 1.0.13

### Improvements
* Events being written by HECWriter in bulk, need to contain source and host keys

## Version 1.0.12

### Bug fixes

* Conf manager can't return correct app name for each conf file.

## Version 1.0.11

### New features and APIs

* Enhance conf manager to provide stanza access info.
* Enhance conf manager to provide interface to create conf file.
* Enhance conf manager to provide interface to check stanza existence.

### Bug fixes

* Reset root logger by root logger file.
* Con manager throw KeyError exception when updating nonexistent encypted keys

## Version 1.0.10

### New features and APIs

* Enhance server_info to get server guid info.

## Version 1.0.9

### New features and APIs

* Enhance conf manager to support multiple conf files management.

### Bug fixes

* Refactor `credentials`, `timer_queue`, `event_writer` and `modular_input`.
* Fix realm in `conf_manager` for credentials.

## Version 1.0.8

### New features and APIs

* Enhance modular input to support get configurations from other input.

## Version 1.0.7

### Bug fixes

* `is_shc_member` returns true on standalone instance.

## Version 1.0.6

### Bug fixes

* Escape proxy username/password in `SplunkRestClient`.
* Update typo in event_writer.py.
* Check `maintenance_mode_flag` in `is_captain_ready()`.

### New features and APIs

* Expose extra parameter `qsize` for `ClassicEventWriter`.
* A simple utility to extract `scheme`, `host` and `port` from http url.

## Version 1.0.5

### Bug fixes

* Miss sortedcontainers dependence in setup.py.

## Version 1.0.4

### New features and APIs

* Enhance server_info to detect captain's service ready status.

## Version 1.0.3

### Bug fixes

* HECEventWriter get max HEC event size by query from limits.
* Auto detect scheme/host/port breaks HECEventWriter.
* HEC config class support.

### New features and APIs

* A simple multi-threading safe timer queue with O(LogN) time complexity.
* Support a new parser/verifier for datatime string with time zone.

## Version 1.0.2

### New features and APIs

* Enhance splunk_rest_client APIs to support local splunkd access without passing
  scheme, host and port which will be auto discovered. This simplify all of the clients.
* Add http connection pooling switch to splunk_rest_client. By default the http connection pooling
  is not turned on, but for KVStore checkpointer and Http Event Writer, the http connection pooling
  is turned on.

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
