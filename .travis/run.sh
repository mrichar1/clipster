#!/bin/bash

set -e
set -x

# Commented out py3 specific apps until #2442/3 resolved:
# https://github.com/travis-ci/apt-package-whitelist/issues
#if [[ $TRAVIS_PYTHON_VERSION == 3* ]]; then
#  PEP8="python3 /usr/lib/python3/dist-packages/pep8.py"
#  PYLINT=/usr/bin/pylint3
#else
  PEP8=/usr/bin/pep8
  PYLINT=/usr/bin/pylint
#fi

# Ignore imports not at start and line-too-long)
$PEP8 --ignore=E402,E501 clipster
$PYLINT --errors-only clipster

python tests/tests.py
