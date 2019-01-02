while [ "$#" -gt 0 ]; do
    case "$1" in
        --postfix) version_postfix=$2; shift 1;;
    esac
    shift
done
username=`awk -F '=' '{if (! ($0 ~ /^;/) && $0 ~ /username/) print $2}' ~/.artifactory_python.cfg`
password=`awk -F '=' '{if (! ($0 ~ /^;/) && $0 ~ /password/) print $2}' ~/.artifactory_python.cfg`
cred="${username}:${password}"
cred=$(echo $cred | tr -d ' ')
name=`awk '/^Name: .*$/ {print $2}' solnlib.egg-info/PKG-INFO`
version=`awk '/^__version__.*$/ {print $3}' solnlib/__init__.py | tr -d "\'"`
new_version=`echo $version | sed -e 's/-dev./.dev/g'`
new_version="${new_version}-${version_postfix}"

uri=$(curl -Ssu $cred -GET https://repo.splunk.com/artifactory/api/storage/pypi/$name/$version/$name-$version.tar.gz | node -pe "JSON.parse(require('fs').readFileSync('/dev/stdin').toString()).uri")
if [[ $uri == "undefined" ]]
then
    echo {\"exists\": true, \"version\":\"${new_version}\"} > upload_check.json
else
    echo {\"exists\": false, \"version\":\"${new_version}\"} > upload_check.json
fi