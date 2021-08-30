#!/bin/bash
pycodestyle --ignore=E402,E501 clipster
pylint --errors-only clipster
python3 tests/tests.py

