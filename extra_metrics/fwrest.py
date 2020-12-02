import requests
from prometheus_client import Histogram
from .logs import logger
from extra_metrics.fwrestendpoint import FWRestEndpoints
from .queries import query_client_info
import json


http_request_time_taken = Histogram('extra_metrics_http_request_time_taken',
                                    'Response time (s)', ['method'])


http_request_time_taken_get_client_info = http_request_time_taken.labels(
    'get_client_info')
http_request_time_taken_get_applications = http_request_time_taken.labels(
    'get_applications')
http_request_time_taken_get_software_updates_web = http_request_time_taken.labels(
    'get_software_updates_web')

# TODO: all these methods should return either s or json, but how is one supposed to know from the name?


class FWRestQuery(FWRestEndpoints):
    def __init__(self, hostname, api_key, verify_tls=True):
        super().__init__(hostname, api_key, verify_tls)

    def get_definition_for_query_id_j(self, query_id):
        r = requests.get(self.endpoint_inventory_query_definition(query_id),
                         headers=self._auth_headers(), verify=self.verify_tls)
        self._check_status(r, 'get_definition_for_query_id_j')
        if r.status_code == 200:
            return r.json()

        return None

    def get_results_for_query_id(self, query_id):
        r = requests.get(self.endpoint_inventory_query_results(query_id),
                         headers=self._auth_headers(), verify=self.verify_tls)
        self._check_status(r, 'get_results_for_query_id')
        return r

    def find_group_with_name(self, group_name):
        # get the group, is it there?
        r = requests.get(self.endpoint_groups_tree(), headers=self._auth_headers(), verify=self.verify_tls)
        self._check_status(r, 'find_group_with_name')
        if r.status_code == 200:
            for item in r.json()["groups_hierarchy"]:
                if item["name"] == group_name:
                    return item

        return None

    def ensure_inventory_query_group_exists(self, group_name):
        existing_group = self.find_group_with_name(group_name)
        if existing_group is not None:
            return existing_group, False
        group_create_data = json.dumps({"name": group_name})
        requests.post(self.endpoint_reports_groups(), headers=self._auth_headers(), verify=self.verify_tls,
            data=group_create_data)
        return self.find_group_with_name(group_name), True

    def get_all_inventory_queries(self):
        r = requests.get(self.inventory_query_str('query/'),
                         headers=self._auth_headers(), verify=self.verify_tls)

        self._check_status(r, 'get_all_inventory_queries')
        if r.status_code == 200:
            return json.loads(r.content)

        return None

    def create_inventory_query(self, json_str):
        # just create only, don't validate if it exists....
        return requests.post(self.inventory_query_str('query/'),
                             headers=self._auth_headers(),
                             verify=self.verify_tls,
                             data=json_str)

    @http_request_time_taken_get_client_info.time()
    def get_client_info_j(self):
        r = requests.post(self.inventory_query_str('query_result/'),
                          headers=self._auth_headers(),
                          verify=self.verify_tls,
                          data=query_client_info)

        self._check_status(r, 'get_client_info_j')
        if r.status_code == 200:
            return r.json()

        return None

    @http_request_time_taken_get_software_updates_web.time()
    def get_software_updates_web_ui_j(self):
        r = requests.get(self.endpoint_web_software_update(), headers=self._auth_headers(), verify=self.verify_tls)
        self._check_status(r, 'get_software_updates_web_ui_j')
        if r.status_code == 200:
            return r.json()

        return None
