Useful Dashboard Info
=

The purpose is to inject queries and configuration into a Dashboard capable FileWave installation.

The motivator was Alex Fredlake's request for the following types of visualizations:
1. [DONE] Chart of different OS types and how many you have of each
2. [DONE] Chart of last time devices have checked in. (last 24 hours, last 7 days, last month, longer) 
3. Chart of what model of devices (What windows product models you have and number of each) 
4. [DONE] Windows OS types, ( Chart of how many on each type of build) 
5. How many of each macOS, Android, iOS version. table for each
6. Chart based on last Windows security update window. (Show how frequently your devices have pulled software updates, in a time frame window like 2)
7. How many devices have location enabled 
8. How many devices have Office installed, and what version. 
9. Devices with high usability, vs low usability (maybe something with login time and application usage).
10. Who is online now? Client devices - it's useful to know if I can work with the device right now.  Is a particular [smart] group online now?  This is OK to be restricted to remote devices, e.g. when doing remote control to know that this will/should work?
11. The list of outstanding fileset deployment delays. 

The visualizations require data collection (inventory queries), aggregation of some sort and a dashboard panel.

Queries
-

Aggregation
-

Panels
-

Examples
=

| Description | Aggregation | Panel Type | Links to |
| ----------- | ------------| ---------- | -------- |
| Different Client OS types | by OS name | Pie Chart | Web list of devices
| Last time devices checked in | Time buckets | Bar Chart | Web list of devices
| Chart of device models | by device model | Pie Chart | Web list of devices
| Windows OS Types | by OS build | Pie Chart | WLoD
| How many of each OS version for macOS, Android, iOS | by OS type, then version | Bar chart? | WLoD
| Windows security updates | | | |
| How many devices have Office Installed and what version | group by Office version, count | Pie Chart | WLoD
| Devices with high CPU usage | special case, requires client scripts - and more investigation

Architecture & Implementation
==
There are lots of tools available within the FileWave system to help implement the dashboard data collection and aggregation.  This script uses as much as possible of the existing tools to get the job done. 

Manually
==

Fix up the Dashboard
-
Fix the stupid query for model number in the main Dashboard page.  


    Log in as root. 
    
    $ cd /usr/local/etc/filewave/grafana/provisioning/dashboards
    $ vi FileWave-Main.json
  
    Replace `filewave_model_version` with `filewave_model_version{job=\"fwxserver-admin\"}`, save the file.

    $ sudo fwcontrol server restart

Fix up the SSL/bearer token configuration for Prometheus dynamic queries
-
The current prometheus configuration for aggregation of inventory queries is incorrectly configured because it is missing the bearer_token configuration line.  Without the bearer token the queries cannot be executed for aggregation.

    Login as root

    $ cd /usr/local/etc/filewave/prometheus
    $ sudo vi prometheus.yml

    Find the following extra-config-https chunk, and add the 'bearer_token_file' line to it: 
```yaml
- job_name: 'extra-config-https'
  scheme: https
  bearer_token_file: './conf.d/bearer_token_file'
  tls_config:
    insecure_skip_verify: true
  file_sd_configs:
    - files:
      - /usr/local/etc/filewave/prometheus/conf.d/jobs/https/*.yml
```

    $ sudo fwcontrol server restart

    To validate that this worked; use http://localhost:21090/targets and ensure that the target called extra-config-https is blue.  If it is red; then something went wrong. 


Add in a job to scrap the Python metrics we're about to run
-
The following configuration step will be auto discovered & loaded - there is no need to restart any server.  Write the following text to a file called:

> /usr/local/etc/filewave/prometheus/conf.d/jobs/http/histo.yml

```yaml
- targets: ['localhost:8000']
  labels:
    purpose: "checkin"
```

To check this has been added correctly; go into the Prometheus targets section on `http://localhost:21090/targets` and look for the extra-config-http configuration you just added.

In the last column of the targets display you should see an error as shown below - because the server hasn't been started yet: 
> Get http://localhost:8000/metrics: dial tcp [::1]:8000: connect: connection refused

Don't skip this - SSL Certs
-
Make darn sure you have an SSL certificate, it must be valid, trusted by everyone (not just the server) and absolutely under no circumstances should it be self signed.  

Just do this - you'll save yourself untold pain.  Trust me I'm still healing.


Checking how long since check in
-
Something like this should help: 

    select u.name, u.id, i.last_check_in, now()::date - i.last_check_in::date how_old, dc.filewave_model_number, i.id from admin.user_clone_group u, public.generic_genericclient i, public.generic_genericdesktopclient dc where u.id = i.filewave_id and i.id = dc.genericclient_ptr_id;

The above statement produces: 

```sql
   name   | id  |         last_check_in         | how_old | filewave_model_number | id 
---------+-----+-------------------------------+---------+-----------------------+----
 hades   | 227 | 2020-03-01 17:58:27.211223+00 |       8 |                    23 |  3
 mini    | 223 | 2020-03-09 11:28:02.645236+00 |       0 |                    25 |  1
 TinyAir | 243 | 2020-03-09 11:28:10.569433+00 |       0 |                    25 |  4
```

Install the virtualenv and Python script on the server
-
This system should be running on the server.  It'll collect interesting information into a bunch of metrics allowing some of the panels to be created; the first use case for this was the PostgreSQL query used to calc the number of days since a device last checked in.  In this case we don't want to suck each device out of the server just to calculate a number - especially not a nice solution when there are 1000's of devices.

Installation instructions for the python module.

    $ virtualenv env
    $ source env/bin/activate
    $ pip install fw-dashboard-extras
    
