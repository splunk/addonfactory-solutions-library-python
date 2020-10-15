# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import print_function
import sys
import os
import os.path as op
import shutil

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib.splunkenv import make_splunkhome_path
from solnlib.splunkenv import get_splunk_bin
import context

splunk_bin = get_splunk_bin()
source_dir = op.join(op.dirname(op.abspath(__file__)), "data", context.app)
target_dir = make_splunkhome_path(["etc", "apps", context.app])
solnlib_lib_dir = op.join(op.dirname(op.dirname(op.abspath(__file__))), "solnlib")
solnlib_lib_target_dir = make_splunkhome_path(
    ["etc", "apps", context.app, "bin", "solnlib"]
)


def setup_environment():
    print("Setup solnlib demo environment...")
    print("Copying %s to %s" % (source_dir, target_dir))
    shutil.copytree(source_dir, target_dir)
    shutil.copytree(solnlib_lib_dir, solnlib_lib_target_dir)
    os.system(splunk_bin + " start")


def teardown_environment():
    print("Teardown solnlib demo environment...")
    os.system(splunk_bin + " stop")
    print("Removing %s" % target_dir)
    if op.exists(target_dir):
        shutil.rmtree(target_dir)


def run_test():
    import test_splunkenv
    import test_server_info
    import test_kvstore
    import test_metadata
    import test_acl
    import test_credentials
    import test_conf_manager
    import test_user_access
    import test_hec_config
    import test_hec_event_writer
    import test_time_parser

    print("check splunk environment...")
    test_splunkenv.test_splunkenv()
    print("check splunk server info...")
    test_server_info.test_server_info()
    print("test kvstore...")
    test_kvstore.test_kvstore()
    print("test metadata reader...")
    test_metadata.test_metadata_reader()
    print("test acl manager...")
    test_acl.test_acl_manager()
    print("test credential manager...")
    test_credentials.test_credential_manager()
    print("test conf manager...")
    test_conf_manager.test_conf_manager()
    print("test user access...")
    test_user_access.test_user_access()
    print("test hec config...")
    test_hec_config.test_hec_config()
    print("test hec eventwriter...")
    test_hec_event_writer.test_hec_event_writer()
    print("test time parser...")
    test_time_parser.test_time_parser()


if __name__ == "__main__":
    teardown_environment()
    setup_environment()
    run_test()
    print("Run tests success.")
