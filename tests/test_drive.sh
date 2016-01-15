# export SPLUNK_HOME=/Applications/Splunk
# export SPLUNK_HOME=/opt/splunk
source $SPLUNK_HOME/bin/setSplunkEnv
python test_file_monitor.py
python test_log.py
python test_orphan_process_checker.py
python test_orphan_process_monitor.py
python test_splunk_platform.py
python test_utils.py
