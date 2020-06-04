from prometheus_client import start_http_server, Histogram, Gauge
import argparse
import yaml
import random
import time
import sys
import os, datetime
import requests

# from rest import FWRestRequestor
from queries import query_client_info, query_software_patches

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# should_fix = False
fw_hostname = 'fwsrv.cluster8.tech'
fw_inv_auth = 'ezBlNWFlNTYwLTQzZWEtNDMwYS1iNTA0LTlmZTkxODFjODAxNH0='

fw_url_runquery = 'https://' + fw_hostname + ':20445/inv/api/v1/query_result/'
fw_auth_headers = { 'Authorization': fw_inv_auth, 'Content-Type': 'application/json' }

def p_ok(msg):
    print(bcolors.OKGREEN, msg, bcolors.ENDC)
def p_fail(msg):
    print(bcolors.FAIL, msg, bcolors.ENDC)

software_patches = Gauge('software_patches_by_critical', 'list of the outstanding software patches', ["name", "is_critical"])
client_checkin_duration_days = Gauge('device_checkin_days', 'the number of days elapsed since a device checked in', ["days",])

def collect_patch_data():
    r = requests.post(fw_url_runquery, headers=fw_auth_headers, data=query_software_patches)
    j = r.json()
    try:
        # summary by patch/criticality

        assert j["fields"]
        assert j["fields"][2] == "Update_name", "field is expected to be the the name of the Update"

        crit_updates = dict()
        normal_updates = dict()

        for v in j["values"]:
            update_name = v[2]
            is_critical = v[6]

            if is_critical:
                crit_updates[update_name] = 1 if not update_name in crit_updates else crit_updates[update_name] + 1
            else:
                normal_updates[update_name] = 1 if not update_name in normal_updates else normal_updates[update_name] + 1
    
        for k,v in crit_updates.items():
            software_patches.labels(k, True).set(v)
        for k,v in normal_updates.items():
            software_patches.labels(k, False).set(v)

    except AssertionError as e1:
        print("The validation/assertions failed: %s" % (e1,))    

def collect_client_data():
    r = requests.post(fw_url_runquery, headers=fw_auth_headers, data=query_client_info)
    j = r.json()

    try:
        assert j["fields"]
        assert j["fields"][6] == "Client_last_check_in", "field 6 is expected to be the Client's last check in date/time"

        buckets = [0, 0, 0, 0]
        now = datetime.datetime.now()

        for v in j["values"]:
            # it's all a bit reliant on knowing what the query was at this point, the way we return data
            # from FW isn't really JSON standard.           
            print(v[6])
            checkin_date = datetime.datetime.strptime(v[6], '%Y-%m-%dT%H:%M:%S.%fZ')
            delta = now - checkin_date
            print("checkin days:", v[0], delta.days)
            checkin_days = delta.days
            if(checkin_days <= 1):
                buckets[0] += 1
            elif checkin_days <= 7:
                buckets[1] += 1
            elif checkin_days <= 30:
                buckets[2] += 1
            else:
                buckets[3] += 1

        client_checkin_duration_days.labels('Less than 1').set(buckets[0])
        client_checkin_duration_days.labels('Less than 7').set(buckets[1])
        client_checkin_duration_days.labels('Less than 30').set(buckets[2])
        client_checkin_duration_days.labels('More than 30').set(buckets[3])

    except AssertionError as e1:
        print("The validation/assertions failed: %s" % (e1,))


def serve_and_process():
    print("Off we go, Ctrl-C to stop... ")

    # Serve these stats... via glorius and wonderful http
    start_http_server(8000)
    # This was made in a container.

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
    # else:

    serve_and_process()

