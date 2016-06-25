#!/bin/bash

source /etc/profile
export LC_ALL=C

set -e

CUR_DIR=$(dirname "$0")

RELEASE_CHECK_ENV=${CUR_DIR}/solution_lib_release_env

if [[ -d "${RELEASE_CHECK_ENV}" ]]; then
    rm -rf "${RELEASE_CHECK_ENV}"
fi

virtualenv ${RELEASE_CHECK_ENV}

source ${RELEASE_CHECK_ENV}/bin/activate

pip install pytest
pip install pytest-cov

pushd ${CUR_DIR}/..

python setup.py build
python setup.py install

python setup.py test
python examples/main.py

python docs/auto_doc.py
make -C docs html

rm -rf build
rm -rf dist
rm -rf solnlib.egg-info
rm -rf tests/__pycache__

find ./ -name "*.pyc"|xargs rm -rf

popd

deactivate

rm -rf "${RELEASE_CHECK_ENV}"
