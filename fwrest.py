import requests
from prometheus_client import Histogram
from queries import query_client_info, query_software_patches, query_client_info, query_win_applications

http_request_time_taken = Histogram('http_request_time_taken', 
    'Response time (s)', ['method'])

http_request_time_taken_get_client_info = http_request_time_taken.labels('get_client_info')
http_request_time_taken_get_software_patches = http_request_time_taken.labels('get_software_patches')
http_request_time_taken_get_applications = http_request_time_taken.labels('get_applications')
http_request_time_taken_get_software_updates_web = http_request_time_taken.labels('get_software_updates_web')

class FWRestQuery:
    def __init__(self, hostname, api_key):
        self.hostname = hostname
        self.api_key = api_key
        super()

    def _fw_run_inv_query(self):
        return 'https://' + self.hostname + ':20445/inv/api/v1/query_result/'
    def _fw_run_web_query(self, additional):
        return 'https://' + self.hostname + '/api/' + additional

    def _auth_headers(self):
        return { 'Authorization': self.api_key, 'Content-Type': 'application/json' }

    # @http_request_time_taken_get_client_info.time()
    def get_client_info(self):
        with http_request_time_taken.labels('get_client_info').time():
            return requests.post(self._fw_run_inv_query(),
                headers=self._auth_headers(), 
                data=query_client_info)
    
    @http_request_time_taken_get_software_patches.time()
    def get_software_patches(self):
        return requests.post(self._fw_run_inv_query(),
            headers=self._auth_headers(), 
            data=query_software_patches)

    @http_request_time_taken_get_software_updates_web.time()
    def get_software_updates_web_ui(self):
        return requests.get(self._fw_run_web_query('updates/ui'),
            headers=self._auth_headers())

    @http_request_time_taken_get_applications.time()
    def get_win_applications(self):
        return requests.post(self._fw_run_inv_query(),
            headers=self._auth_headers(), 
            data=query_win_applications)
