#!/bin/bash

set -e
set -x

# Ignore imports not at start and line-too-long)
pep8 --ignore=E402,E501 clipster
pylint --errors-only clipster

python tests/tests.py
