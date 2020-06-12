from fwrest import FWRestQuery
import json, sys, os
import pandas as pd
from main import retrieve_all_queries_in_group, create_default_queries_in_group
from queries import query_software_patches

pd.set_option('display.precision', 3)
pd.set_option('display.expand_frame_repr', False)

fw_query = FWRestQuery(
    hostname = 'fwsrv.cluster8.tech',
    api_key = 'ezBlNWFlNTYwLTQzZWEtNDMwYS1iNTA0LTlmZTkxODFjODAxNH0='
)

query_group, was_created = fw_query.ensure_inventory_query_group_exists("Extra Metrics Queries - Apps")
group_id = query_group["id"]
print(f"group_id: {group_id}, {was_created}")
if was_created:
    create_default_queries_in_group(group_id)
retrieve_all_queries_in_group(group_id)

sys.exit(5)

r = fw_query.get_software_updates_web_ui()
j = r.json()

assert j["next"] is None
r = j["results"]

# print("we got:")
# print(json.dumps(r, indent=2))


# I want to: 
#
# read the software updates web UI into Pandas
# 
# group by update/platform/criticality 

values = [ 
    [ 
        t["id"], 
        t["update_id"], 
        t["platform"], 
        t["critical"], 
        t["name"]["display_value"],
        t["count_unassigned"],
        t["assigned_clients_count"]["assigned"],
        t["assigned_clients_count"]["completed"],
        t["assigned_clients_count"]["remaining"],                
        t["assigned_clients_count"]["warning"],
        t["assigned_clients_count"]["error"],
        t["import_error"]
    ] for t in r 
]
    
columns = [
    "id",
    "update_id",
    "platform",
    "is_critical",
    "name",
    "unassigned_count",
    "assigned",
    "completed",
    "remaining",
    "warning",
    "error",
    "import_error"
]

df = pd.DataFrame(values, columns=columns)
print(df)

t8 = df['assigned'].sum()
print(f"assigned: {df['assigned'].sum()}, completed: {df['completed'].sum()}")

ru = df.groupby(["platform", "is_critical"], as_index=False)["update_id"].count()
print(ru)
for i in ru.to_numpy():
    print(f"wheee {i[0]}, crit: {i[1]}, count: {i[2]}")

