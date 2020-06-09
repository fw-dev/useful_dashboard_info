from prometheus_client import start_http_server, Histogram, Gauge
import pandas as pd
import argparse
import yaml
import random
import time
import sys
import os, datetime

from fwrest import FWRestQuery

fw_query = FWRestQuery(
    hostname = 'fwsrv.cluster8.tech',
    api_key = 'ezBlNWFlNTYwLTQzZWEtNDMwYS1iNTA0LTlmZTkxODFjODAxNH0='
)

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

software_updates_by_device = Gauge('software_updates_by_device', 
    'list of devices and the number of [critical] updates they need to have installed', 
    ["device_name", "is_update_critical"])

software_updates_by_platform = Gauge('software_updates_by_platform', 
    'list of platforms and the number of [critical] updates they have available', 
    ["platform_name", "is_update_critical"])

device_checkin_days = Gauge('device_checkin_days', 
    'various interesting stats on a per device basis, days since checked, compliance status', 
    ["days",])

device_information = Gauge('device_information',
    'various interesting stats on a per device basis, days since checked, compliance status',
    ["device_name", "platform", "compliant", "tracked", "locked", "fw_client_version"])

inventory_query = Gauge('inventory_query_elapsed_seconds',
    'the time taken to run inventory queries, along with info about whether they are used in smart groups or just reports'
    )

def collect_patch_data():
    r = fw_query.get_software_patches()
    j = r.json()

    df = pd.DataFrame(j["values"], columns=j["fields"])
    platform_mapping = {
        "0": "Apple",
        "1": "Microsoft"
    }

    software_updates_by_platform.labels(platform_mapping["0"], False).set(0)
    software_updates_by_platform.labels(platform_mapping["1"], False).set(0)

    ru = df.groupby(["Client_filewave_client_name", "Update_critical"], as_index=False)["Update_name"].count()
    for i in ru.to_numpy():
        client_name = i[0]
        is_crit = i[1]
        update_count = i[2]
        print(client_name, is_crit, update_count)
        software_updates_by_device.labels(client_name, is_crit).set(update_count)

    ru = df.groupby(["Update_platform", "Update_critical"], as_index=False)["Update_name"].count()
    for i in ru.to_numpy():
        platform_name = platform_mapping[i[0]]
        is_crit = i[1]
        update_count = i[2]
        print(platform_name, is_crit, update_count)
        software_updates_by_platform.labels(platform_name, is_crit).set(update_count)


def collect_client_data():
    Client_device_name = 0
    Client_filewave_client_locked = 1
    # Client_free_disk_space = 2
    # Client_device_id = 3
    Client_is_tracking_enabled = 4
    # Client_location = 5
    # Client_serial_number = 6
    DesktopClient_filewave_client_version = 7
    # Client_management_mode = 8
    # Client_filewave_client_name = 9
    # Client_filewave_id = 10
    # OperatingSystem_version = 11
    # Client_enrollment_state = 12
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

            device_information.labels(
                v[Client_device_name],
                v[OperatingSystem_name],
                True, # compliant
                v[Client_is_tracking_enabled],
                v[Client_filewave_client_locked],
                v[DesktopClient_filewave_client_version]
            ).set(v[DesktopClient_filewave_model_number] if v[DesktopClient_filewave_model_number] is not None else 0)

            print("checkin days:", v[0], checkin_days)

            if(checkin_days <= 1):
                buckets[0] += 1
            elif checkin_days <= 7:
                buckets[1] += 1
            elif checkin_days <= 30:
                buckets[2] += 1
            else:
                buckets[3] += 1

        device_checkin_days.labels('Less than 1').set(buckets[0])
        device_checkin_days.labels('Less than 7').set(buckets[1])
        device_checkin_days.labels('Less than 30').set(buckets[2])
        device_checkin_days.labels('More than 30').set(buckets[3])

    except AssertionError as e1:
        print("The validation/assertions failed: %s" % (e1,))


def serve_and_process():
    print("Off we go, Ctrl-C to stop... ")

    # Serve these stats... via glorius and wonderful http
    start_http_server(8000)

    try:
        while(True):
            collect_client_data()
            collect_patch_data()
            time.sleep(30)
    except Exception as e:
        print("Closing...", e)


if __name__ == "__main__":
    # # by default, no params, we are simply going to run and serve metrics - but there's more!
    # p = argparse.ArgumentParser(description='Serve up some additional / custom metrics specific to FileWave')
    # p.add_argument('--validate', action='store_true', help='validate the server installation before running this tool')
    # p.add_argument('--fix', action='store_true', help='during validation, try to fix problems as well')

    # args = p.parse_args()
    # if args.fix:
    #     should_fix = True

    # if args.validate:
    #     validate_server_installation()

    serve_and_process()

