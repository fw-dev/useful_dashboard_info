from prometheus_client import start_http_server, Gauge

import logging
import timeloop
import random
import time
import sys
import os, json
import datetime
import threading
import pandas as pd 

from extra_metrics.application import ApplicationQueryManager
from extra_metrics.softwarepatches import SoftwarePatchStatus
from extra_metrics.devices import PerDeviceStatus
from extra_metrics.fwrest import FWRestQuery
from extra_metrics.config import ExtraMetricsConfiguration, read_config_helper
from extra_metrics.logs import logger, init_logging

init_logging()

# TODO: the app titles should be based on the query

# TODO: why does Mozilla show nothing - reg-exp ?

# TODO: update docs on upgrade for pie chart

# TODO: changing the time is a pain in the butt, doesn't carry to new dashboards
# TODO: add annotations in for model update to the dashboards

# TODO: link to devices affected in the dashboard is wrong; we can fix that!  https://${server}/reports/46/details/

# TODO: can I subscribe to FW query updates to run the app queries again?  or just the single app query?

# TODO: if the configuration of the FW server changes, how does this product keep up? 

# TODO: DEVICE HEALTH show the reasons/state of health of a device in (my app or) custom fields so it can be reported on

# TODO: consider alerts for devices entering a non-healthy state for the first time today

# TODO: consider how I might achieve a cannibalization test for devices? 

# TODO: write documentation on arch and reasoning... perhaps using the Wiki in GitHub.

# TODO: languages / translation?

tl = timeloop.Timeloop()

app_qm = None
software_patches = None
per_device = None

pd.set_option('display.precision', 3)
pd.set_option('display.expand_frame_repr', False)


@tl.job(interval=datetime.timedelta(seconds=30))
def validate_and_collect_data():
    app_qm.validate_query_definitions()
    app_qm.collect_application_query_results()

    software_patches.collect_patch_data_status()
    software_patches.collect_patch_data_per_device()

    per_device.collect_client_data(software_patches)

def serve_and_process():
    cfg = ExtraMetricsConfiguration()
    read_config_helper(cfg)

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


