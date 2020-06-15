# FileWave Extra Metrics
The purpose of Extra Metrics is to augment a standard FileWave installation with additional metrics and dashboard capabilities. 

# Overview
Extra Metrics provides a series of dashboards and prometheus metrics related to how your fleet's deployments are progressing.  The information can be used to show "at-a-glance" insights into the software patch status, device health and user specific deployments.

Example dashboards are included in this project; and will be installed automatically. 

# Requirements
Before you begin - it's very important to ensure that you meet the requirements for this additional module. 

Minimum FileWave System Requirements: 
1. The Extra Metrics system runs only on the Linux version of FileWave
1. FileWave Version 14+: Extra Metrics requires version 14 or higher of the FileWave product.  It will fail to configure on anything less.
2. SSH: You will need SSH access to your FileWave Server.
3. Create an API Key specifically for this module (with inventory *create* rights).
4. Ensure your server has SSL certificates - self signed certs are not enough. 

# Installation
These instructions assume you will be installing Extra Metrics directly on your FileWave Server, which already has Python3.7 (or later) installed.

> We *highly* recommend installing Extra Metrics into its own virtual environment.  Doing so ensures that the introduction of this module cannot interfere with the operational integrity of your FileWave Server.  

> DO NOT INSTALL EXTRA METRICS DIRECTLY INTO THE PYTHON RUNTIME ENVIRONMENT OF YOUR FILEWAVE SERVER.  

> If you are unsure about the above statement - STOP - contact your FileWave SE or support.  Your FileWave Server installation can be destroyed by mis-understanding the impact of this configuration.

## Steps
Assuming you are already logged into your FileWave Server using SSH, follow along to set up the virtual environment, install the Extra Metrics package and configure it for use. 

For the purpose of these instructions we are assuming a non-root user called gregor has been created.

    $ /usr/local/filewave/python/bin/pyvenv $HOME/extra-metrics
    $ source $HOME/extra-metrics/bin/activate

Now your terminal prompt will change - the name of the virtual env should show up:

    (extra-metrics) $ pip install filewave-extra-metrics

Now the python package is installed; before completing configuration you need an API Key (and SSL certs)    

## Create & configure an Inventory API Key
Extra Metrics should be configured with an Inventory API Key in order to access Inventory and create the inventory groups and queries.

> Please create a unique access token (API Key) for the Extra Metrics module

Once you have the API key; use the following command: 

    $ which extra-metrics-config
    $ sudo <full path extra-metrics-config>/extra-metrics-config --api-key 'EzblNWflNTYwLtQzZWEtNDMwYc1iNTa1LTlmZTkxODFjODAyNH0=' --external-dns-name 'fwserver.mydomain.com'

You will see output similar to the following, confirming that the dashboards have been imported, YAML files written and that you are ready to go!



## Upgrading
To upgrade the Extra Metrics module; just run the install command again but include an '--upgrade' flag. 

    $ pip install --upgrade filewave-extra-metrics


## Hint: don't skip this - SSL Certs
Make sure you have an SSL certificate, it must be valid, trusted by everyone (not just the server) and absolutely under no circumstances should it be self signed.  

Just do this - you'll save yourself untold pain.  Trust me I'm still healing.

Reference
=
Adjust supervisorctl to include --storage.tsdb.allow-overlapping-blocks?

# Developers

To upload to PyPi, ensure you have the credentials in a pypi.config file (not checked into source control), then the ./rebuild_for_pypi.sh and ./upload_to_pypi.sh scripts are your friends. 

An example pypi.config file contains: 

```
[pypi]
username = __token__
password = pypi-AgEIcH.....<add your really long token here>
```

# What information is exported by Extra Metrics?

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
