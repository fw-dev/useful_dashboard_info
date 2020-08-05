#!/bin/bash
export PYTHONPATH=$CWD:$PYTHONPATH
export EXTRA_METRICS_LOGLEVEL=DEBUG
coverage run --branch -m unittest discover 