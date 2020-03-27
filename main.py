from prometheus_client import start_http_server, Histogram, Gauge
import argparse
import yaml
import random
import time
import sys
import os
import requests

from rest import FWRestRequestor
from queries import query_client_info

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

should_fix = False
fw_hostname = 'fwsrv.cluster8.tech'
fw_inv_auth = 'e2VlNjJjYTU1LTAzNDMtNDQ2ZS04ODJkLTQwYTE1Nzg2MzQ1MX0='

fw_url_runquery = 'https://' + fw_hostname + ':20445/inv/api/v1/query_result/'
fw_auth_headers = { 'Authorization': fw_inv_auth, 'Content-Type': 'application/json' }

def p_ok(msg):
    print(bcolors.OKGREEN, msg, bcolors.ENDC)
def p_fail(msg):
    print(bcolors.FAIL, msg, bcolors.ENDC)

client_checkin_duration_days = Gauge('device_checkin_days', 'the number of days elapsed since a device checked in', ["days",])

# collect_statement = "select u.name, u.id, i.last_check_in, now()::date - i.last_check_in::date how_old, " \
#         "i.id from admin.user_clone_group u, public.generic_genericclient i " \
#         " WHERE u.id = i.filewave_id "

def collect_client_data():
    r = requests.post(fw_url_runquery, headers=fw_auth_headers, data=query_client_info)


# this task will run every minute
# def collect_via_pg():
#     try:
#         pass
        
#         conn = psycopg2.connect(host=fw_host, port=fw_port, database="mdm", user="django")

#         cur = conn.cursor()
#         cur.execute(collect_statement)
#         rows = cur.fetchall()

#         # print("got %d rows" % (cur.rowcount))
#         buckets = [0, 0, 0, 0]
        
#         for row in rows:
#             # print(row)

#             checkin_days = row[3]
#             if(checkin_days <= 1):
#                 buckets[0] += 1
#             elif checkin_days <= 7:
#                 buckets[1] += 1
#             elif checkin_days <= 30:
#                 buckets[2] += 1
#             else:
#                 buckets[3] += 1

#             client_checkin_duration_days.labels('Less than 1').set(buckets[0])
#             client_checkin_duration_days.labels('Less than 7').set(buckets[1])
#             client_checkin_duration_days.labels('Less than 30').set(buckets[2])
#             client_checkin_duration_days.labels('More than 30').set(buckets[3])

#         if conn is not None:
#             print("stats collected - used %d rows: buckets: %s", (cur.rowcount, buckets))
#             conn.close()
#     except Exception as reason: # for any reason...
#         print("Failed to collect info from the MDM system - aborting: ", reason)


def validate_server_installation():
    # can we write/access the configuration for prometheus? 
    prom_config_path = os.path.join("/usr/local/etc/filewave/prometheus/", "prometheus.yml")    
    if not os.access(prom_config_path, os.W_OK):
        raise Exception("I don't seem to be able to write to %s, aborting..." % (prom_config_path,))

    fixes = 0
    prom_config = None

    # does the prometheus.yml file contain the bearer token reference in the extra-config-https section? 
    with open(prom_config_path, 'r') as file:
        token_key = 'bearer_token_file'
        prom_config = yaml.safe_load(file)
        for item in prom_config['scrape_configs']:
            job_name = item['job_name']
            if job_name == 'extra-config-https':
                try:
                    bearer_token = item[token_key]
                    # oh, it's there - excellent...
                    p_ok("Key %s present in config with value: %s - pass" % (token_key, bearer_token))
                except KeyError:
                    fixes += 1
                    item[token_key] = './conf.d/bearer_token_file'
                    p_fail("%s is NOT present in the config - FAILED" % (token_key,))

    if fixes == 1 and should_fix:
        with open(prom_config_path, 'w') as file:
            yaml.dump(prom_config, file, sort_keys=False)
            print("Re-wrote the prometheus configuration at %s" % (prom_config_path,))


    # ok, do we have the job that ensures prometheus will call us? 
    our_prom_config_file = os.path.join("/usr/local/etc/filewave/prometheus/conf.d/jobs/http/useful_dashboard_prom_config.yml")
    if not os.path.exists(our_prom_config_file):
        p_fail("%s is NOT present on disk - which means prometheus won't scrape this process - FAILED" % (our_prom_config_file,))
    else:
        p_ok("our prometheus configuration appears to be on disk - pass")
 

    # does the main fwxserver model version have the right spec? 
    grep_command = "grep filewave_model_version /usr/local/etc/filewave/grafana/provisioning/dashboards/FileWave-Main.json | grep fwxserver-admin"
    exit_code = os.system(grep_command)
    if exit_code != 0:
        p_fail("The /usr/local/etc/filewave/grafana/provisioning/dashboards/FileWave-Main.json needs 'fwxserver-admin' added to it - FAILED")        
        fixes += 1
    else:
        p_ok("configuration for the main dashboard (model number) looks ok - pass")

    return fixes


def serve_and_process():
    print("Off we go, Ctrl-C to stop... ")

    # Serve these stats... via glorius and wonderful http
    start_http_server(8000)
    # This was made in a container.

    try:
        while(True):
            # collect_via_pg()
            collect_client_data()
            time.sleep(30)
    except:
        print("Closing...")


if __name__ == "__main__":
    # by default, no params, we are simply going to run and serve metrics - but there's more!
    p = argparse.ArgumentParser(description='Serve up some additional / custom metrics specific to FileWave')
    p.add_argument('--validate', action='store_true', help='validate the server installation before running this tool')
    p.add_argument('--fix', action='store_true', help='during validation, try to fix problems as well')

    args = p.parse_args()
    if args.fix:
        should_fix = True

    if args.validate:
        validate_server_installation()
    else:
        serve_and_process()

