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

from application import ApplicationQueryManager
from compliance import ClientCompliance
from fwrest import FWRestQuery

from logs import logger, init_logging

init_logging()

# from flask import Flask
# from werkzeug.middleware.dispatcher import DispatcherMiddleware
# app = Flask(__name__)

# app_dispatch = DispatcherMiddleware(app, {
#     '/metrics': make_wsgi_app()
# })

fw_query = FWRestQuery(
    hostname = 'fwsrv.cluster8.tech',
    api_key = 'ezBlNWFlNTYwLTQzZWEtNDMwYS1iNTA0LTlmZTkxODFjODAxNH0='
)

tl = timeloop.Timeloop()
app_qm = ApplicationQueryManager(fw_query)

pd.set_option('display.precision', 3)
pd.set_option('display.expand_frame_repr', False)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def p_ok(msg):
    print(bcolors.OKGREEN, msg, bcolors.ENDC)
def p_fail(msg):
    print(bcolors.FAIL, msg, bcolors.ENDC)

software_updates_by_device = Gauge('extra_metrics_software_updates_by_device', 
    'list of devices and the number of [critical] updates they need to have installed', 
    ["device_name", "device_id", "is_update_critical"])

software_updates_by_platform = Gauge('extra_metrics_software_updates_by_platform', 
    'list of platforms and the number of [critical] updates they have available', 
    ["platform_name", "is_update_critical"])

software_updates_by_state = Gauge('extra_metrics_software_updates_by_state', 
    'buckets of all the software updates, according to the number of devices in each state',
    ["state"])

device_checkin_days = Gauge('extra_metrics_devices_by_checkin_days', 
    'various interesting stats on a per device basis, days since checked, compliance status', 
    ["days",])

device_information = Gauge('extra_metrics_per_device_information',
    'various interesting stats on a per device basis, days since checked, compliance status',
    ["device_name", "platform", "compliant", "tracked", "locked", "fw_client_version"])


def collect_application_data():
    app_qm.validate_query_definitions()
    app_qm.collect_application_query_results()


def collect_patch_data_via_web_ui():
    r = fw_query.get_software_updates_web_ui()
    j = r.json()

    assert j["next"] is None
    r = j["results"]

    # goal: number of software updates, grouped by status:
    # status values:
    # NEW: count_unassigned
    # IN PROGRESS: count_assigned
    # FAILED: assigned_clients.error + assigned_clients.warning
    # DONE: assigned_clients.remaining == 0

    # later: so how can Pandas groupby a code expression? 
    counters = {
        "assigned": 0,
        "completed": 0,
        "remaining": 0,
        "warning": 0,
        "error": 0
    }

    # values = [
    #     [
    #         t["assigned_clients_count"]
    #     ]
    # ]

    for item in r:
        acc = item["assigned_clients_count"]
        counters["assigned"] += acc["assigned"]
        counters["completed"] += acc["completed"]
        counters["remaining"] += acc["remaining"]
        counters["warning"] += acc["warning"]
        counters["error"] += acc["error"]

    software_updates_by_state.labels('Assigned').set(counters["assigned"])
    software_updates_by_state.labels('Completed').set(counters["completed"])
    software_updates_by_state.labels('Remaining').set(counters["remaining"])
    software_updates_by_state.labels('Warning').set(counters["warning"])
    software_updates_by_state.labels('Error').set(counters["error"])

'''
TODO: get the software patches tied into clients. 
TODO: why does the device by client version shown Unknown?

For monday 15th June 2020: 

To get software updates: use the test.py code

Go to work and get my laptop?

Then to populate health per device, pull inventory data - group all updates by client_name and start counting

Question: if ALL updates are actually deployed, does this work? 

'''
def collect_patch_data_via_inventory():
    r = fw_query.get_software_patches()
    j = r.json()

    df = pd.DataFrame(j["values"], columns=j["fields"])
    platform_mapping = {
        "0": "Apple",
        "1": "Microsoft"
    }

    ru = df.groupby(["Client_filewave_client_name", "Client_filewave_id", "Update_critical"], as_index=False)["Update_name"].count()
    for i in ru.to_numpy():
        client_name = i[0]
        client_id = int(i[1])
        is_crit = i[2]
        update_count = i[3]
        logger.info(f"patches, device: {client_name}/{client_id}, critical: {is_crit}, number of updates: {update_count}")
        software_updates_by_device.labels(client_name, client_id, is_crit).set(update_count)

    ru = df.groupby(["Update_platform", "Update_critical"], as_index=False)["Update_name"].count()
    for i in ru.to_numpy():
        platform_name = platform_mapping[i[0]]
        is_crit = i[1]
        update_count = i[2]
        software_updates_by_platform.labels(platform_name, is_crit).set(update_count)


def collect_client_data():
    Client_device_name = 0
    Client_filewave_client_locked = 1
    Client_free_disk_space = 2
    # Client_device_id = 3
    Client_is_tracking_enabled = 4
    # Client_location = 5
    # Client_serial_number = 6
    DesktopClient_filewave_client_version = 7
    Client_management_mode = 8
    # Client_filewave_client_name = 9
    # Client_filewave_id = 10
    OperatingSystem_version = 11
    # Clienpyt_enrollment_state = 12
    OperatingSystem_name = 13
    # OperatingSystem_edition = 14
    # OperatingSystem_build = 15
    # OperatingSystem_type = 16
    Client_last_check_in = 17
    DesktopClient_filewave_model_number = 18
    # DesktopClient_device_manufacturer = 19
    # Client_last_logged_in_username = 20
    # Client_device_product_name = 21
    # Client_current_upstream_host = 22
    # Client_current_upstream_port = 23
    Client_total_disk_space = 24

    r = fw_query.get_client_info()
    j = r.json()
    
    try:
        assert j["fields"]
        assert j["fields"][Client_device_name] == "Client_device_name", "field 0 is expected to be the Client's name"
        assert j["fields"][Client_last_check_in] == "Client_last_check_in", "field 17 is expected to be the Client's last check in date/time"

        buckets = [0, 0, 0, 0]
        now = datetime.datetime.now()

        for v in j["values"]:          
            # if there is no last check in date, we want to assume it's NEVER checked in 
            checkin_days = 99
            if v[Client_last_check_in] is not None:
                checkin_date = datetime.datetime.strptime(v[Client_last_check_in], '%Y-%m-%dT%H:%M:%S.%fZ')
                delta = now - checkin_date
                checkin_days = delta.days

            comp_check = ClientCompliance(
                v[Client_total_disk_space],
                v[Client_free_disk_space],
                checkin_days
            )

            client_ver = v[DesktopClient_filewave_client_version]
            if client_ver is None:
                client_ver = "Unknown"

            # TODO: when rolling this up, if we have another entry that is non-null in any of the columns
            # and this row IS null; drop this row. 
            device_information.labels(
                v[Client_device_name],
                v[OperatingSystem_name],
                comp_check.get_compliance_state(), # compliant state, see class above
                v[Client_is_tracking_enabled],
                v[Client_filewave_client_locked],
                client_ver 
            ).set(v[DesktopClient_filewave_model_number] if v[DesktopClient_filewave_model_number] is not None else 0)

            logger.info(f"info, device: {v[Client_device_name]}, os: {v[OperatingSystem_name]}, client_ver: {client_ver}")

            if(checkin_days <= 1):
                buckets[0] += 1
            elif checkin_days < 7:
                buckets[1] += 1
            elif checkin_days < 30:
                buckets[2] += 1
            else:
                buckets[3] += 1

        device_checkin_days.labels('Less than 1').set(buckets[0])
        device_checkin_days.labels('Less than 7').set(buckets[1])
        device_checkin_days.labels('Less than 30').set(buckets[2])
        device_checkin_days.labels('More than 30').set(buckets[3])

    except AssertionError as e1:
        print("The validation/assertions failed: %s" % (e1,))


@tl.job(interval=datetime.timedelta(seconds=30))
def validate_and_collect_data():
    collect_application_data()
    collect_client_data()
    collect_patch_data_via_inventory()
    collect_patch_data_via_web_ui()


def serve_and_process():
    # be a web server... go on...
    start_http_server(8000)

    # collect the first chunk of info from our server
    validate_and_collect_data()

    # just sit here being a web server...
    tl.start(block=True)

# TODO: make this all run on setup.py - and maybe Flask with a single process task?
if __name__ == "__main__":
    serve_and_process()

