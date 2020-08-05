from prometheus_client import Gauge

import traceback
import pkg_resources
import pandas as pd
import json
import sys

from extra_metrics.package import get_package_resource_json
from .fwrest import http_request_time_taken
from .logs import logger


app_version_count = Gauge('extra_metrics_application_version',
    'a summary of how many devices are using a particular app & version',
    ["query_name", "application_version", "query_id"])


class ApplicationUsageRollup:
    """
    Application Usage - Rollup

    The idea is to run a FW query, use Pandas to do a [multi] column rollup and count the number of instances
    per version of the application.

    Once the counts have been made; they are stored and would be ready to pull out and put into a metric, that
    isn't part of this class though.
    """
    def __init__(self, query_id, rollup_column_names, op_column_name, op="count"):
        self.query_id = query_id
        self.rollup_column_names = rollup_column_names if isinstance(rollup_column_names, list) else [rollup_column_names]
        self.op_column_name = op_column_name
        self.op = op
        self.result_df = None

    def exec(self, fw_rest_api):
        r = fw_rest_api.get_results_for_query_id(self.query_id)
        j = r.json()
        df = pd.DataFrame(j["values"], columns=j["fields"])
        # run the group-by and count operation
        self.result_df = df.groupby(self.rollup_column_names, as_index=False)[self.op_column_name].count()

    def results(self):
        return self.result_df.to_numpy()


class ApplicationQueryManager:
    """
    Responsible for managing the refresh of queries for apps from the FW server, associating that
    with the rolled up results (via ApplicationUsageRollup)
    """
    def __init__(self, fw_query):
        self.fw_query = fw_query
        self.app_queries = {}

    def is_query_valid(self, q_id):
        app_name = False
        app_version = False
        client_id = False

        # fetch the query def
        json_query = self.fw_query.get_definition_for_query_id_j(q_id)
        if json_query is None:
            return False

        # requires id/name too
        if "name" not in json_query:
            return False

        if "id" not in json_query:
            return False

        # we are expecting Application_name, Application_version and Client_filewave_id
        fields_array = json_query["fields"]
        for item in fields_array:
            if item["column"] == "name" and item["component"] == "Application":
                app_name = True
            if item["column"] == "version" and item["component"] == "Application":
                app_version = True
            if item["column"] == "device_id" and item["component"] == "Client":
                client_id = True

        return app_name and app_version and client_id

    def create_default_queries_in_group(self, group_id):
        for query_file in pkg_resources.resource_listdir("extra_metrics", "app_queries"):
            if query_file.endswith(".json"):
                json_data = get_package_resource_json("extra_metrics.app_queries", query_file)
                json_data["group"] = group_id
                self.fw_query.create_inventory_query(json.dumps(json_data))

    def retrieve_all_queries_in_group(self, group_id):
        # in all cases - read all queries in this group and find their IDs, store in-mem for redirection
        all_queries = self.fw_query.get_all_inventory_queries()

        self.app_queries = {}
        for q in all_queries:
            q_group = q["group"]
            q_id = q["id"]
            if q_group == group_id and self.is_query_valid(q_id):
                self.app_queries[q_id] = q
                logger.info(f"refreshed app query {q_id}/{q['name']}")

    def validate_query_definitions(self):
        # ensure there is a top level query group we can place queries into...
        query_group, was_created = self.fw_query.ensure_inventory_query_group_exists("Extra Metrics Queries - Apps")
        if query_group is not None:
            logger.debug(f"found group: {query_group}")
            group_id = int(query_group['id'])

            # if we created this group; then pre-pop the queries with what we have in code, otherwise
            # assume the queries inside this group are definitive
            if was_created:
                self.create_default_queries_in_group(group_id)

            self.retrieve_all_queries_in_group(group_id)
        else:
            logger.warning("The inventory group named 'Extra Metrics Queries - Apps' could not be found - not refreshing queries")

    def collect_application_query_results(self):
        for q_id, q in self.app_queries.items():
            r = ApplicationUsageRollup(q_id, ["Application_name", "Application_version"], "Client_device_id")

            try:
                label_name = f"app_query_{q['name']}"
                with http_request_time_taken.labels(label_name).time():
                    r.exec(self.fw_query)

                for result in r.results():
                    name = q['name']
                    version = result[1]
                    total = int(result[2])
                    logger.info(f"app query result for {name}, {version}, query_id: {r.query_id} = {total}")
                    app_version_count.labels(name, version, r.query_id).set(total)
            except Exception as e:
                logger.error(f"failed to do app query rollup on query id {q_id}, {e}")
                traceback.print_exc(file=sys.stdout)
