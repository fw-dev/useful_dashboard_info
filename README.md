# FileWave Extra Metrics
The purpose of Extra Metrics is to augment a standard FileWave installation with additional metrics and dashboard capabilities. 

_TODO: get the dashboards loaded (via a command?) into the system, likely prompt the user or just import them during configuration, will need another API key for that?  If running on fwxserver, can we work out that API key?  Importing *might* be as simple as jamming the files into the provisioning directory actually_

# Overview
Extra Metrics provides a series of dashboards related to how your fleet's deployments are progressing.  The information is intended to show "at-a-glance" insights into the software patch status, device health and user specific deployments.

_TODO: screen shots in the readme._

## Software Patch Status
The software update (patch status) of clients is calculated using software  update catalogs as well as information delivered by clients about the updates they require. 

Panels provided:
- A birds eye view of the entire fleet's patch status - represented via percentage numbers of patch deployment, grouped by state (success, pending installation and warning/error).  
- Numbers related to (critical) updates that are not fully deployed. 
- Links into the FileWave web UI to make remediation or further investigation easier. 

## Device Health
The whole fleet of devices is continuously sending data back to the FileWave Inventory system which is used to calculate device health.  

Panels provided: 
- Device health summary - a grouping of all devices by health state.  The health of a device is calculated as follows: 
 - TBD (disk space, outstanding patches)
 - _TODO: show the reasons/state of health of a device in custom fields so it can be reported on_
 - _TODO: consider alerts for devices entering a non-healthy state for the first time today_


# Installation
Extra Metrics can be installed into any Python3 system using pip.  These instructions assume you will be installing Extra Metrics on your FileWave Server, which already has Python3.7 (or later) installed.

Extra Metrics is on PyPy, and as such can be installed with pip: 

    $ sudo /usr/local/filewave/python/bin/python3 pip install filewave-extra-metrics
    
This installs the module and executables.  Once installed, the system must be connected to FileWave and correctly set up.   

> Configuring filewave-extra-metrics to run on another host depends on what that host is and is therefore not covered here. 

## Don't skip this - SSL Certs
Make sure you have an SSL certificate, it must be valid, trusted by everyone (not just the server) and absolutely under no circumstances should it be self signed.  

Just do this - you'll save yourself untold pain.  Trust me I'm still healing.

## Configure FileWave to pull information from the Extra Metrics module
The Extra Metrics module contains commands to inject the appropriate configuration into your FileWave system automatically. 

To ensure the FileWave Dashboard system is pulling data from Extra Metrics; run the following command:

    $ extra-metrics-install-prometheus-config

Create & configure an Inventory API Key
-
Extra Metrics should be configured with an Inventory API Key in order to access Inventory and create the inventory groups and queries.

The following permissions are required for the API Key; these can be set up in the Manage Administrators tool -> Application Tokens interface.  

Note: ** please create a unique access token (API Key) for the Extra Metrics module ** - if you ever need to revoke the token you will only affect this module and nothing else. 

Once you have the API key; use the following command: 

  $ extra-metrics-configure --api-key 'ezBlNWFlNTYwLTQzZWEtNDMwYS1iNTA0LTlmZTkxODFjODAxNH0=' --external-dns-name 'fwsrv.cluster8.tech'

_TODO: write the commands for this using click and store/use the configuration_

Reference
=
Adjust supervisorctl to include --storage.tsdb.allow-overlapping-blocks?
