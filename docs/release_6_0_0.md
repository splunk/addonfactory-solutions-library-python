# Removed requests from solnlib

The `requests` library has been removed from solnlib, so solnlib now depends on the `requests` library from the running environment.
By default, splunk delivers `requests` whose version depends on the splunk version. More information [here](https://docs.splunk.com/Documentation/Splunk/9.2.3/ReleaseNotes/Credits).

Please note that if `requests` are installed in `<Add-on>/lib` e.g. as a dependency of another library, that version will be taken first. 
If `requests` are missing from the add-on's `lib` directory, then `requests` provided from splunk will be used. In case the splunk `requests` version is not sufficient for you,
you can deliver version you need by simply adding it to the `requirements.txt` or `pyproject.toml` file in your add-on.
