import requests
from prometheus_client import Histogram
from queries import query_client_info, query_software_patches, query_client_info, query_win_applications
import json


http_request_time_taken = Histogram('http_request_time_taken',
                                    'Response time (s)', ['method'])


http_request_time_taken_get_client_info = http_request_time_taken.labels(
    'get_client_info')
http_request_time_taken_get_software_patches = http_request_time_taken.labels(
    'get_software_patches')
http_request_time_taken_get_applications = http_request_time_taken.labels(
    'get_applications')
http_request_time_taken_get_software_updates_web = http_request_time_taken.labels(
    'get_software_updates_web')


class FWRestQuery:
    def __init__(self, hostname, api_key):
        self.hostname = hostname
        self.api_key = api_key
        super()

    def _fw_run_inv_query(self, additional=None):
        return 'https://' + self.hostname + ':20445/inv/api/v1/' + additional

    def _fw_run_web_query(self, additional):
        return 'https://' + self.hostname + '/api/' + additional

    def _auth_headers(self):
        return {'Authorization': self.api_key, 'Content-Type': 'application/json'}

    def get_results_for_query_id(self, query_id):
        return requests.get(self._fw_run_inv_query(f'query_result/{query_id}'),
                             headers=self._auth_headers())

    def find_group_with_name(self, group_name):
        # get the group, is it there?
        r = requests.get(self._fw_run_web_query(
            'reports/groups_tree'), headers=self._auth_headers())
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
        print(f"data payload is: {group_create_data}")
        r = requests.post(self._fw_run_web_query('reports/groups/'),
                          headers=self._auth_headers(),
                          data=group_create_data)

        return self.find_group_with_name(group_name), True

    def get_all_inventory_queries(self):
        r = requests.get(self._fw_run_inv_query('query/'),
            headers=self._auth_headers())
        if r.status_code == 200:
            return json.loads(r.content)
        return None

    def create_inventory_query(self, json_str):
        # just create only, don't validate if it exists....
        return requests.post(self._fw_run_inv_query('query/'),
                            headers=self._auth_headers(),
                            data=json_str)

    @http_request_time_taken_get_client_info.time()
    def get_client_info(self):
        return requests.post(self._fw_run_inv_query('query_result/'),
                             headers=self._auth_headers(),
                             data=query_client_info)

    @http_request_time_taken_get_software_patches.time()
    def get_software_patches(self):
        return requests.post(self._fw_run_inv_query('query_result/'),
                             headers=self._auth_headers(),
                             data=query_software_patches)

    @http_request_time_taken_get_software_updates_web.time()
    def get_software_updates_web_ui(self):
        return requests.get(self._fw_run_web_query('updates/ui/?limit=10000'),
                            headers=self._auth_headers())

    @http_request_time_taken_get_applications.time()
    def get_win_applications(self):
        return requests.post(self._fw_run_inv_query('query_result/'),
                             headers=self._auth_headers(),
                             data=query_win_applications)


if __name__ == "__main__":
    fw_query = FWRestQuery(
        hostname = 'fwsrv.cluster8.tech',
        api_key = 'ezBlNWFlNTYwLTQzZWEtNDMwYS1iNTA0LTlmZTkxODFjODAxNH0='
    )

    r = fw_query.get_results_for_query_id(109)
    if r.status_code == 200:
        j = r.json()
        print(json.dumps(j, indent=2))
    else:
        print("problem: ", r)