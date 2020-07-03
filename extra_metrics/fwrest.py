import requests
from prometheus_client import Histogram
from .logs import logger
import re
from .queries import query_client_info, query_software_patches
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

class FWRestQuery:
    def __init__(self, hostname, api_key, verify_tls=True):
        self.hostname = hostname
        self.api_key = api_key
        self.verify_tls = verify_tls
        super()

    def _fw_run_inv_query(self, additional=None):
        return 'https://' + self.hostname + ':20445/inv/api/v1/' + additional

    def _fw_run_web_query(self, additional):
        return 'https://' + self.hostname + '/api/' + additional

    def _auth_headers(self):
        return {'Authorization': self.api_key, 'Content-Type': 'application/json'}

    def _check_status(self, r, method_name):
        if r.status_code != 200:
            logger.warn(f"{method_name}, status: {r.status_code}, {r}")
            if r.status_code == 401:  # rejected; just abort
                raise Exception(
                    "401 not allowed - implies the API Key has been revoked; aborting")

    def get_current_fw_version_major_minor_patch(self):
        # uses /api/config/app to get version information - format is "app_version": "14.0.0<-something>"
        r = requests.get(self._fw_run_web_query('config/app'), headers=self._auth_headers(), verify=self.verify_tls)
        self._check_status(r, 'get_current_fw_version')

        j_value = r.json()
        if j_value is None:
            raise Exception("Obtaining major/minor/patch info from the server didnt return data; aborting")
        if "app_version" not in j_value:
            raise Exception("app_version data isnt in the returned data from the fw server; aborting")

        exp = re.compile(r'(\d+).(\d+).(\d+)-(.*)', re.IGNORECASE)
        match_result = re.search(exp, j_value["app_version"])
        major, minor, patch = 0, 0, 0
        if match_result is not None:
            major = int(match_result.group(1))
            minor = int(match_result.group(2))
            patch = int(match_result.group(3))
            return major, minor, patch
        return None, None, None

    def get_definition_for_query_id_j(self, query_id):
        r = requests.get(self._fw_run_inv_query(f'query/{query_id}'),
                         headers=self._auth_headers(), verify=self.verify_tls)
        self._check_status(r, 'get_definition_for_query_id_j')
        if r.status_code == 200:
            return r.json()

        return None

    def get_results_for_query_id(self, query_id):
        r = requests.get(self._fw_run_inv_query(f'query_result/{query_id}'),
                         headers=self._auth_headers(), verify=self.verify_tls)
        self._check_status(r, 'get_results_for_query_id')
        return r

    def find_group_with_name(self, group_name):
        # get the group, is it there?
        r = requests.get(self._fw_run_web_query(
            'reports/groups_tree'), headers=self._auth_headers(), verify=self.verify_tls)

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
        requests.post(self._fw_run_web_query('reports/groups/'),
                      headers=self._auth_headers(),
                      verify=self.verify_tls,
                      data=group_create_data)

        return self.find_group_with_name(group_name), True

    def get_all_inventory_queries(self):
        r = requests.get(self._fw_run_inv_query('query/'),
                         headers=self._auth_headers(), verify=self.verify_tls)

        self._check_status(r, 'get_all_inventory_queries')
        if r.status_code == 200:
            return json.loads(r.content)

        return None

    def create_inventory_query(self, json_str):
        # just create only, don't validate if it exists....
        return requests.post(self._fw_run_inv_query('query/'),
                             headers=self._auth_headers(),
                             verify=self.verify_tls,
                             data=json_str)

    @http_request_time_taken_get_client_info.time()
    def get_client_info_j(self):
        r = requests.post(self._fw_run_inv_query('query_result/'),
                          headers=self._auth_headers(),
                          verify=self.verify_tls,
                          data=query_client_info)

        self._check_status(r, 'get_client_info_j')
        if r.status_code == 200:
            return r.json()

        return None

    @http_request_time_taken_get_software_updates_web.time()
    def get_software_updates_web_ui_j(self):
        r = requests.get(self._fw_run_web_query('updates/extended_list/?limit=10000'),
                         headers=self._auth_headers(), verify=self.verify_tls)

        self._check_status(r, 'get_software_updates_web_ui_j')
        if r.status_code == 200:
            return r.json()

        return None
