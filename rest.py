import requests

class FWRestRequestor:
    def __init__(self, fw_hostname=None, fw_api_key=None):
        self.fw_api_hostname = fw_hostname
        self.fw_api_auth = fw_api_key
        

   