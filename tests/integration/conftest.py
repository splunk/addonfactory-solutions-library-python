import os
import sys

# path manipulation get the 'splunk' library for the imports while running on GH Actions
sys.path.append(
    os.path.sep.join([os.environ["SPLUNK_HOME"], "lib", "python3.7", "site-packages"])
)
# TODO: 'python3.7' needs to be updated as and when Splunk has new folder for Python.
