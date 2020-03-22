from prometheus_client import start_http_server, Histogram
import random
import time

_INF = float("inf")
MINS_PER_DAY = 1440

buckets = (30, 60, MINS_PER_DAY / 2, MINS_PER_DAY, MINS_PER_DAY * 7, MINS_PER_DAY * 30, _INF)
observations = 10

# Create a metric to mimic check in times for client devices
m = Histogram('device_checkin_time', 
    'How long since a client last checked in, units are minutes, accurate to within the frequency that the script is executed', 
    buckets=buckets)

for b in range(1, observations):
    m.observe(random.randint(1, b))

if __name__ == "__main__":
    # Serve these stats...
    start_http_server(8000)
    # This was made in a container.

    while(True):
        m.observe(random.randint(1, MINS_PER_DAY * 40))
        time.sleep(1)