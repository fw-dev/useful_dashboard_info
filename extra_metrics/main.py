from prometheus_client import start_http_server, make_wsgi_app, Histogram, Gauge

import logging
import timeloop
import pandas as pd
import yaml
import random
import time
import sys
import os, json
import datetime
import threading

from extra_metrics.application import ApplicationQueryManager
from extra_metrics.softwarepatches import SoftwarePatchStatus
from extra_metrics.devices import PerDeviceStatus
from extra_metrics.fwrest import FWRestQuery
from extra_metrics.config import ExtraMetricsConfiguration, read_config_helper
from extra_metrics.logs import logger, init_logging

init_logging()

# TODO: show the reasons/state of health of a device in custom fields so it can be reported on

# TODO: consider alerts for devices entering a non-healthy state for the first time today

# TODO: get the dashboards loaded (via a command?) into the system, likely prompt the user or just import them during configuration, will need another API key for that?  If running on fwxserver, can we work out that API key?  Importing *might* be as simple as jamming the files into the provisioning directory actually_

# TODO: Dump the dashboards into source control before packaging and sending out for the first time 

# TODO: write documentation on arch and reasoning... perhaps using the Wiki in GitHub.

tl = timeloop.Timeloop()

app_qm = None
software_patches = None
per_device = None

pd.set_option('display.precision', 3)
pd.set_option('display.expand_frame_repr', False)

# TODO configuration here for delay.. not hard coded.... 
@tl.job(interval=datetime.timedelta(seconds=30))
def validate_and_collect_data():
    app_qm.validate_query_definitions()
    app_qm.collect_application_query_results()

    per_device.collect_client_data()

    software_patches.collect_patch_data_status()
    software_patches.collect_patch_data_per_device()


def serve_and_process():
    cfg = ExtraMetricsConfiguration()
    read_config_helper(cfg)

    # TODO: run a call to check all runtime assumptions we need, abort if they are not there....

    # TODO: can I use this?  get the hostname via curl -X GET "https://fwsrv.cluster8.tech/api/config/app"
    fw_query = FWRestQuery(hostname=cfg.get_fw_api_server(), api_key=cfg.get_fw_api_key())

    global app_qm, software_patches, per_device

    app_qm = ApplicationQueryManager(fw_query)
    software_patches = SoftwarePatchStatus(fw_query)
    per_device = PerDeviceStatus(fw_query)

    # be a web server... go on...
    start_http_server(8000)

    # collect the first chunk of info from our server
    validate_and_collect_data()

    # just sit here being a web server...
    tl.start(block=True)


