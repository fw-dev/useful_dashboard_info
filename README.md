Useful Dashboard Info
=

The purpose is to inject queries and configuration into a Dashboard capable FileWave installation.

The motivator was Alex Fredlake's request for the following types of visualizations:
1. [DONE] Chart of different OS types and how many you have of each
2. [DONE] Chart of last time devices have checked in. (last 24 hours, last 7 days, last month, longer) 
3. BAR GRAPH - Chart of what model of devices (What windows product models you have and number of each) 
4. [DONE] Windows OS types (Chart of how many on each type of build) 
5. How many of each macOS, Android, iOS version. table for each
6. Chart based on last Windows security update window. (Show how frequently your devices have pulled software updates, in a time frame window like 2)
7. [DONE] How many devices have location enabled 
8. How many devices have Office installed, and what version. 
9. Devices with high usability, vs low usability (maybe something with login time and application usage).
10. Who is online now? Client devices - it's useful to know if I can work with the device right now.  Is a particular [smart] group online now?  This is OK to be restricted to remote devices, e.g. when doing remote control to know that this will/should work?
11. The list of outstanding fileset deployment delays. 

Software Compliance
=

Information we have: 
- all the software updates that are available
- all the software updates that are being requested by clients (creation date, )

Show me: 
- [older] security updates that are critical that are NOT installed (where?)
  - number of outstanding critical updates, split by OS
  - number of clients affected by the critical updates
  - list of devices that don't have the updates
- percentage of fleet that isn't 100% protected by critical updates
- how many critical updates still haven't been installed 1 week after they were made available

1. Number of critical updates that are not fully deployed. 




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

Fix up the SSL/bearer token configuration for Prometheus dynamic queries - is was entirely missing from my setup when I last loaded it.  Copy the base64 token into a bearer_token_file located at: /usr/local/etc/filewave/prometheus/conf.d

Add port 21090 to access prometheus targets for debugging them:

    sudo firewall-cmd --zone=public --add-port=21090/tcp --permanent
    sudo firewall-cmd --reload

Add in a job to scrap the Python metrics we're about to run.
-
The following configuration step will be auto discovered & loaded - there is no need to restart any server.  Write the following text to a file called:

> /usr/local/etc/filewave/prometheus/conf.d/jobs/http/histo.yml

```yaml
- targets: ['localhost:8000']
  labels:
    purpose: "checkin"
```

Don't skip this - SSL Certs
-
Make darn sure you have an SSL certificate, it must be valid, trusted by everyone (not just the server) and absolutely under no circumstances should it be self signed.  

Just do this - you'll save yourself untold pain.  Trust me I'm still healing.

Load up the Client Data Query
-
The file called 'query_dashboard_info_clients.json' needs to be loaded into the FW server. 

    curl -s -k -H "Authorization: ezBlNWFlNTYwLTQzZWEtNDMwYS1iNTA0LTlmZTkxODFjODAxNH0=" -d "@query_dashboard_info_clients.json" -X POST "https://fwsrv.cluster8.tech:20445/inv/api/v1/query/"

** this does not yet work **

Fetch the query to store on disk for the future
-
The queries can be stored on disk.

    curl -s -k -H "Authorization: ezBlNWFlNTYwLTQzZWEtNDMwYS1iNTA0LTlmZTkxODFjODAxNH0=" https://fwsrv.cluster8.tech:20445/inv/api/v1/query/45 > by_su_critical.json
