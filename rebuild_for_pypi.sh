#!/bin/bash
if [ -d dist ]; then
    rm dist/*
fi

python setup.py sdist bdist_wheel