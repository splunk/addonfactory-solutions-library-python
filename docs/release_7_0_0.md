# Removed usage of btool command from solnlib

As of version 7.0.0, the `btool` command has been removed from solnlib. Configuration stanzas and keys should now be accessed via the REST API. 
Additionally, the `splunkenv` module can only be used in environments where Splunk is installed, as it relies on Splunk-specific methods for making internal calls.

## Session key is now mandatory in some of the functions

The affected functions now require a valid `session_key` to operate correctly. While solnlib attempts to retrieve the `session_key` automatically, 
there are scenarios—such as within a modular input script—where this is not possible. In such cases, you must explicitly provide the `session_key` 
to ensure proper authorization. Affected functions are:

* `get_splunk_host_info`
* `get_splunkd_access_info`
* `get_scheme_from_hec_settings`
* `get_splunkd_uri`
* `get_conf_key_value`
* `get_conf_stanza`

## Changed arguments in `get_conf_key_value` and `get_conf_stanza`

As of version 7.0.0, the following changes have been made to the function:

`get_conf_key_value` now requires 4 mandatory arguments:

* `conf_name`
* `stanza`
* `key`
* `app_name` (new)

`get_conf_stanza` now requires 3 mandatory arguments:

* `conf_name`
* `stanza`
* `app_name` (new)

Both functions also accept the following optional arguments:

* `session_key` - Used for authentication. If not provided, a 401 Unauthorized error may occur depending on the context.
* `users` - Limits results returned by the configuration endpoint. Defaults to `nobody`.
* `raw_output` - If set to `True`, the full decoded JSON response is returned. 
This should be enabled when `app_name` is set to the global context `(/-/)`, as the Splunk REST API may return multiple entries in that case.

## The `get_session_key` function has been removed from solnlib

This function relied on reading the `scheme`, `host` and `port` using the deprecated btool utility, which is no longer supported.

