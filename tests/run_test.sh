version=`awk '/^__version__.*$/ {print $3}' solnlib/__init__.py | tr -d "\'"`
least_significant=$((`echo $version | sed -E "s/.*\.([0-9]+)$/\1/g"`+1))
new_version=`echo $version | sed -E "s/(.*)\.([0-9]+)$/\1.$least_significant/g"`
new_version=$new_version'-dev.'${BUILD_NUMBER}
version=`echo $version | sed 's/\./\\\./g'`
sed -i 's/'$version'/'$new_version'/g' solnlib/__init__.py
npm install --unsafe-perm;
npm run build;
npm run jtest;