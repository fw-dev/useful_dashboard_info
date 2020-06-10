#!/bin/bash

# Assuming prometheus running from a local folder (this same dir)
# Prom will create a 'data' folder. We're importing direct to that.
#
# MUST use the 'tsdb' here (mac only). It's the new one with the 'import' command
./tsdb import backfill_from_existing.txt data/