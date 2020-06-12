import pandas as pd
from fwrest import FWRestQuery

"""
Application Usage - Rollup

The idea is to run a FW query, use Pandas to do a [multi] column rollup and count the number of instances 
per version of the application.

Once the counts have been made; they are stored and would be ready to pull out and put into a metric, that 
isn't part of this class though.
"""
class ApplicationUsageRollup:
    def __init__(self, query_id, rollup_column_name, op_column_name, op="count"):
        self.query_id = query_id
        self.rollup_column_name = rollup_column_name
        self.op_column_name = op_column_name
        self.op = op
        self.result_df = None

    def exec(self, fw_rest_api):
        r = fw_rest_api.get_results_for_query_id(self.query_id)
        j = r.json()
        df = pd.DataFrame(j["values"], columns=j["fields"])
        # run the group-by and count operation
        self.result_df = df.groupby([self.rollup_column_name])[self.op_column_name].sum()


"""
Responsible for managing the refresh of queries for apps from the FW server, associating that 
with the rolled up results (via ApplicationUsageRollup)
"""
class ApplicationQueryManager:
    self.app_queries = {}
    self.app_rollups = {}

    def __init__(self, fw_query):
        self.fw_query = fw_query

    def create_default_queries_in_group(self, group_id):
        app_queries_dir = os.path.join(os.getcwd(), "app_queries")
        for query_file in os.listdir(app_queries_dir):
            if query_file.endswith(".json"):
                with open(os.path.join(app_queries_dir, query_file)) as f:
                    json_data = json.load(f)
                    json_data["group"] = group_id
                    self.fw_query.create_inventory_query(json.dumps(json_data))

    def retrieve_all_queries_in_group(self, group_id):
        # in all cases - read all queries in this group and find their IDs, store in-mem for redirection 
        all_queries = self.fw_query.get_all_inventory_queries()
        
        app_queries = {}
        for q in all_queries:
            q_group = q["group"]
            q_id = q["id"]
            if q_group == group_id:
                app_queries[q_id] = q
                logger.info(f"refreshed app query {q_id}/{q['name']}")

    def validate_query_definitions(self):
        # ensure there is a top level query group we can place queries into...
        query_group, was_created = self.fw_query.ensure_inventory_query_group_exists("Extra Metrics Queries - Apps")
        group_id = int(query_group['id'])

        # if we created this group; then pre-pop the queries with what we have in code, otherwise
        # assume the queries inside this group are definitive
        if was_created:
            self.create_default_queries_in_group(group_id)

        self.retrieve_all_queries_in_group(group_id)

