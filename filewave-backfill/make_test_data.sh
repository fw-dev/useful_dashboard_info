#!/bin/bash

# Limit to 300 metrics only (about 1/3rd what's available)
# Use --help for more
pipenv run ./backfill.py create --url http://fwsrv.cluster8.tech:21090 -l 300