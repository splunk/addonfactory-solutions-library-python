import sys
import os
import os.path as op
import shutil

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from splunksolutionlib.splunkenv import make_splunkhome_path
from splunksolutionlib.splunkenv import get_splunk_bin
import context

splunk_bin = get_splunk_bin()
source_dir = op.join(op.dirname(op.abspath(__file__)), 'data', context.app)
target_dir = make_splunkhome_path(['etc', 'apps', context.app])


def setup_environment():
    print 'Setup environment...'
    print 'Copying %s to %s' % (source_dir, target_dir)
    shutil.copytree(source_dir, target_dir)
    os.system(splunk_bin + ' start')


def teardown_environment():
    print 'Teardown environment...'
    os.system(splunk_bin + ' stop')
    print 'Removing %s' % target_dir
    if op.exists(target_dir):
        shutil.rmtree(target_dir)


def run_test():
    import test_splunkenv
    import test_server_info
    import test_kvstore
    import test_metadata
    import test_app_permissions
    import test_acl
    import test_credentials
    import test_http_request

    print 'check splunk environment...'
    test_splunkenv.test_splunkenv()
    print 'check splunk server info...'
    test_server_info.test_server_info()
    print 'test kvstore...'
    test_kvstore.test_kvstore()
    print 'test metadata reader...'
    test_metadata.test_metadata_reader()
    print 'test app permissions request queue...'
    test_app_permissions.test_app_permissions_request_queue()
    print 'test acl manager...'
    test_acl.test_acl_manager()
    print 'test credential manager...'
    test_credentials.test_credential_manager()
    print 'test http request...'
    test_http_request.test_http_request()

if __name__ == '__main__':
    teardown_environment()
    setup_environment()
    run_test()
