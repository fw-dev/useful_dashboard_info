import re
import requests
from .logs import logger


class FWRestEndpoints:
    def __init__(self, hostname, api_key, verify_tls):
        self.hostname = hostname
        self.api_key = api_key
        self.verify_tls = verify_tls
        self.major_version = 0
        self.minor_version = 0
        self.patch_version = 0

    def _check_status(self, r, method_name):
        if r.status_code != 200:
            logger.warning(f"{method_name}, status: {r.status_code}, {r}")
            if r.status_code == 401:  # rejected; just abort
                raise Exception(
                    "401 not allowed - implies the API Key has been revoked; aborting")

    def inventory_query_str(self, additional=None):
        return 'https://' + self.hostname + ':20445/inv/api/v1/' + additional

    def web_query_str(self, additional):
        return 'https://' + self.hostname + '/api/' + additional

    def _auth_headers(self):
        return {'Authorization': self.api_key, 'Content-Type': 'application/json'}

    def is_version_at_least(self, major, minor, patch):
        if self.major_version > major:
            return True
        elif self.major_version < major:
            return False

        if self.minor_version > minor:
            return True
        elif self.minor_version < minor:
            return False

        return self.patch_version >= patch

    def fetch_server_version(self):
        self.get_current_fw_version_major_minor_patch()

    def get_current_fw_version_major_minor_patch(self):
        # uses /api/config/app to get version information - format is "app_version": "14.0.0<-something>"
        r = requests.get(self.web_query_str('config/app'), headers=self._auth_headers(), verify=self.verify_tls)
        self._check_status(r, 'get_current_fw_version')

        j_value = r.json()
        if j_value is None:
            raise Exception("Obtaining major/minor/patch info from the server didnt return data; aborting")
        if "app_version" not in j_value:
            raise Exception("app_version data isnt in the returned data from the fw server; aborting")

        exp = re.compile(r'(\d+).(\d+).(\d+)-(.*)', re.IGNORECASE)
        match_result = re.search(exp, j_value["app_version"])

        if match_result is not None:
            self.major_version = int(match_result.group(1))
            self.minor_version = int(match_result.group(2))
            self.patch_version = int(match_result.group(3))
            return self.major_version, self.minor_version, self.patch_version
        return None, None, None

    def endpoint_groups_tree(self):
        uri = 'reports/groups_tree'
        if self.is_version_at_least(14, 2, 0):
            uri = 'reports/v1/groups-tree'  # yes, no slash on end
        return self.web_query_str(uri)

    def endpoint_reports_groups(self):
        uri = 'reports/groups/'
        if self.is_version_at_least(14, 2, 0):
            uri = 'reports/v1/groups'  # yes, no slash on end
        return self.web_query_str(uri)

    def endpoint_web_software_update(self):
        uri = 'updates/extended_list/?limit=10000'
        if self.is_version_at_least(14, 2, 0):
            uri = 'updates/v1/extended-list?limit=10000'
        return self.web_query_str(uri)

    def endpoint_inventory_query_definition(self, query_id):
        return self.inventory_query_str(f'query/{query_id}')

    def endpoint_inventory_query_results(self, query_id):
        return self.inventory_query_str(f'query_result/{query_id}')
