import requests
from prometheus_client import Histogram
from queries import query_client_info, query_software_patches, query_client_info

http_request_time_taken = Histogram('http_request_time_taken', 
    'Response time (s)', ['method'])

http_request_time_taken_get_client_info = http_request_time_taken.labels('get_client_info')
http_request_time_taken_get_software_patches = http_request_time_taken.labels('get_software_patches')

class FWRestQuery:
    def __init__(self, hostname, api_key):
        self.hostname = hostname
        self.api_key = api_key
        super()

    def _fw_runquery(self):
        return 'https://' + self.hostname + ':20445/inv/api/v1/query_result/'

    def _auth_headers(self):
        return { 'Authorization': self.api_key, 'Content-Type': 'application/json' }

    @http_request_time_taken_get_client_info.time()
    def get_client_info(self):
        return requests.post(self._fw_runquery(),
            headers=self._auth_headers(), 
            data=query_client_info)

    @http_request_time_taken_get_software_patches.time()
    def get_software_patches(self):
        return requests.post(self._fw_runquery(),
            headers=self._auth_headers(), 
            data=query_software_patches)

