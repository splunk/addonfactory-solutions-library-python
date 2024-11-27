# Removed requests and urllib3 from solnlib

The `requests` and `urllib3` libraries has been removed from solnlib, so solnlib now depends on the `requests` and `urllib3` libraries from the running environment.
By default, Splunk delivers the above libraries and their version depends on the Splunk version. More information [here](https://docs.splunk.com/Documentation/Splunk/9.2.3/ReleaseNotes/Credits).

**IMPORTANT**: `urllib3` is available in Splunk `v8.1.0` and later

Please note that if `requests` or `urllib3` are installed in `<Add-on>/lib` e.g. as a dependency of another library, that version will be taken first.
If `requests` or `urllib3` is missing in the add-on's `lib` directory, the version provided by Splunk will be used. In case the Splunk `requests` or `urllib3` version is not sufficient for you,
you can deliver version you need by simply adding it to the `requirements.txt` or `pyproject.toml` file in your add-on.
