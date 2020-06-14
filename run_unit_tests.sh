#!/bin/bash
# export PYTHONPATH=$CWD:$PYTHONPATH
coverage run --branch -m unittest tests/*.py && coverage html