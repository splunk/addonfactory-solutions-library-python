#
# Copyright 2021 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import os.path as op
import shutil
import sys

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
import context

from solnlib.splunkenv import get_splunk_bin, make_splunkhome_path

splunk_bin = get_splunk_bin()
source_dir = op.join(op.dirname(op.abspath(__file__)), "data", context.app)
target_dir = make_splunkhome_path(["etc", "apps", context.app])
solnlib_lib_dir = op.join(op.dirname(op.dirname(op.abspath(__file__))), "solnlib")
solnlib_lib_target_dir = make_splunkhome_path(
    ["etc", "apps", context.app, "bin", "solnlib"]
)


def setup_environment():
    print("Setup solnlib demo environment...")
    print(f"Copying {source_dir} to {target_dir}")
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
    import test__kvstore
    import test_acl
    import test_conf_manager
    import test_credentials
    import test_hec_config
    import test_hec_event_writer
    import test_splunkenv
    import test_time_parser
    import test_user_access

    print("check splunk environment...")
    test_splunkenv.test_splunkenv()
    print("test kvstore...")
    test__kvstore.test_kvstore()
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
