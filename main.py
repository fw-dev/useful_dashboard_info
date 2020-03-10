from prometheus_client import start_http_server, Histogram, Gauge
import argparse
import psycopg2
import random
import time
import sys

# Create a metric to mimic check in times for client devices
# device_checkin_delay = Histogram('device_checkin_delay', 
#     'How long since a client last checked in, units are days, accurate to within the frequency that the script is executed', 
#     buckets=(1, 7, 30, float("inf")))

client_checkin_duration_days = Gauge('device_checkin_days', 'the number of days elapsed since a device checked in', ["days",])

collect_statement = "select u.name, u.id, i.last_check_in, now()::date - i.last_check_in::date how_old, " \
        "i.id from admin.user_clone_group u, public.generic_genericclient i " \
        " WHERE u.id = i.filewave_id "

# this task will run every minute
def collect_postgres_information():
    try:       
        conn = psycopg2.connect(host="localhost", port=9432, database="mdm", user="django")
        cur = conn.cursor()
        cur.execute(collect_statement)
        rows = cur.fetchall()

        # print("got %d rows" % (cur.rowcount))
        buckets = [0, 0, 0, 0]
        
        for row in rows:
            # print(row)

            checkin_days = row[3]
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

            # device_checkin_delay.observe(checkin_days)

        if conn is not None:
            print("stats collected - used %d rows", (cur.rowcount,))
            conn.close()
    except Exception as reason: # for any reason...
        print("Failed to collect info from the postgres database - aborting for now: ", reason)

if __name__ == "__main__":
    print("Off we go, Ctrl-C to stop... ")

    # Serve these stats... via glorius and wonderful http
    start_http_server(8000)

    try:
        while(True):
            collect_postgres_information()
            time.sleep(30)
    except:
        print("Closing...")

