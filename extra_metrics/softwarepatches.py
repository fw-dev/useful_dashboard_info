from prometheus_client import Gauge
import pandas as pd
from extra_metrics.logs import logger

software_updates_by_state = Gauge('extra_metrics_software_updates_by_state', 
    'buckets of all the software updates, according to the number of devices in each state',
    ["state"])

software_updates_by_device = Gauge('extra_metrics_software_updates_by_device', 
    'list of devices and the number of [critical] updates they need to have installed', 
    ["device_name", "device_id", "is_update_critical"])

software_updates_by_platform = Gauge('extra_metrics_software_updates_by_platform', 
    'list of platforms and the number of [critical] updates they have available', 
    ["platform_name", "is_update_critical"])


class SoftwarePatchStatus:
    def __init__(self, fw_query):
        self.fw_query = fw_query
        self.state_by_patch = {}

    def collect_patch_data_status(self):
        r = self.fw_query.get_software_updates_web_ui()
        j = r.json()

        assert j["next"] is None
        r = j["results"]

        self.state_by_patch = {}

        # goal: number of software updates, grouped by status:
        # status values:
        # NEW: count_unassigned
        # IN PROGRESS: count_assigned
        # FAILED: assigned_clients.error + assigned_clients.warning
        # DONE: assigned_clients.remaining == 0

        counters = {
            "assigned": 0,
            "completed": 0,
            "remaining": 0,
            "warning": 0,
            "error": 0
        }

        for item in r:
            self.state_by_patch[item['update_id']] = item
            
            acc = item["assigned_clients_count"]
            counters["assigned"] += acc["assigned"]
            counters["completed"] += acc["completed"]
            counters["remaining"] += acc["remaining"]
            counters["warning"] += acc["warning"]
            counters["error"] += acc["error"]

        software_updates_by_state.labels('Assigned').set(counters["assigned"])
        software_updates_by_state.labels('Completed').set(counters["completed"])
        software_updates_by_state.labels('Remaining').set(counters["remaining"])
        software_updates_by_state.labels('Warning').set(counters["warning"])
        software_updates_by_state.labels('Error').set(counters["error"])
        
    def collect_patch_data_per_device(self):
        r = self.fw_query.get_software_patches()
        j = r.json()

        df = pd.DataFrame(j["values"], columns=j["fields"])
        platform_mapping = {
            "0": "Apple",
            "1": "Microsoft"
        }

        ru = df.groupby(["Client_filewave_client_name", "Client_filewave_id", "Update_critical"], as_index=False)["Update_name"].count()
        for i in ru.to_numpy():
            client_name = i[0]
            client_id = int(i[1])
            is_crit = i[2]
            update_count = i[3]
            logger.info(f"patches, device: {client_name}/{client_id}, critical: {is_crit}, number of updates: {update_count}")
            software_updates_by_device.labels(client_name, client_id, is_crit).set(update_count)

        ru = df.groupby(["Update_platform", "Update_critical"], as_index=False)["Update_name"].count()
        for i in ru.to_numpy():
            platform_name = platform_mapping[i[0]]
            is_crit = i[1]
            update_count = i[2]
            software_updates_by_platform.labels(platform_name, is_crit).set(update_count)
