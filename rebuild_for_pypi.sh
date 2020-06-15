#!/bin/bash
if [ -d dist ]; then
    rm -rf dist
fi

if [ -d build ]; then   
    rm -rf build
fi

python setup.py sdist bdist_wheel