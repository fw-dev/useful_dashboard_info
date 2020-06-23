from prometheus_client import Gauge
import pandas as pd
from extra_metrics.logs import logger

software_updates_by_state = Gauge('extra_metrics_software_updates_by_state',
    'buckets of all the software updates, according to the number of devices in each state',
    ["state"])

software_updates_by_device = Gauge('extra_metrics_software_updates_by_device',
    'list of devices and the number of [critical] updates they need to have installed',
    ["device_name", "device_id", "is_update_critical"])

software_updates_by_update = Gauge('extra_metrics_software_updates_by_update',
    'list of updates and the number of devices asking to have installed',
    ["update_name", "fw_id"])

software_updates_by_platform = Gauge('extra_metrics_software_updates_by_platform',
    'list of platforms and the number of [critical] updates they have available',
    ["platform_name", "is_update_critical"])


class PerDevicePatchState:
    def __init__(self, client_id):
        self.client_id = client_id
        self.client_name = None
        self.critical_patch_count = 0
        self.standard_patch_count = 0


class SoftwarePatchStatus:
    def __init__(self, fw_query):
        self.fw_query = fw_query
        self.state_by_patch = {}
        # a dictionary of the PerDevicePatchState
        self.state_by_device = {}

    def get_perdevicestate_for_client_id(self, client_id):
        if client_id not in self.state_by_device:
            self.state_by_device[client_id] = PerDevicePatchState(client_id)
        return self.state_by_device.get(client_id, None)

    def collect_patch_data_status(self):
        self.state_by_patch = {}

        j = self.fw_query.get_software_updates_web_ui_j()
        if j is None:
            return

        if "results" not in j or len(j["results"]) == 0:
            logger.info("no results for software update patch status received from FileWave server")
            return None

        columns = [
            "update_name",
            "fw_id",
            "platform",
            "unassigned",
            "assigned",
            "completed",
            "remaining",
            "warning",
            "error"
        ]

        values = [
        ]

        res = j["results"]
        for item in res:
            update_id = item['update_id']
            self.state_by_patch[update_id] = item

            acc = item["assigned_clients_count"]

            item_name = item["name"]
            update_name = item_name["display_value"]
            if item_name["os_type"] == "OSX":
                update_name += f" ({update_id})"

            values.append([
                update_name,
                item["id"],
                item["platform"],
                item["count_unassigned"],
                acc["assigned"],
                acc["completed"],
                acc["remaining"],
                acc["warning"],
                acc["error"]
            ])

        df = pd.DataFrame(values, columns=columns)

        per_update_totals = df.groupby(["update_name", "fw_id"], as_index=False)["unassigned"].sum()
        for item in per_update_totals.to_numpy():
            software_updates_by_update.labels(item[0], item[1]).set(item[2])

        totals = df.sum(0, numeric_only=True)

        # goal: number of software updates, grouped by status:
        # status values:
        # NEW: count_unassigned
        # IN PROGRESS: count_assigned
        # FAILED: assigned_clients.error + assigned_clients.warning
        # DONE: assigned_clients.remaining == 0

        software_updates_by_state.labels('Unassigned').set(totals["unassigned"])
        software_updates_by_state.labels('Assigned').set(totals["assigned"])
        software_updates_by_state.labels('Completed').set(totals["completed"])
        software_updates_by_state.labels('Remaining').set(totals["remaining"])
        software_updates_by_state.labels('Warning').set(totals["warning"])
        software_updates_by_state.labels('Error').set(totals["error"])

    def collect_patch_data_per_device(self):
        self.state_by_device = {}

        j = self.fw_query.get_software_patches_j()
        if j is None:
            return

        if "values" not in j or len(j["values"]) == 0:
            logger.info("no results for software update patch status per device received from FileWave server")
            return None

        if "fields" not in j:
            logger.info("no fields meta data for software update patch status per device received from FileWave server")
            return None

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

            # update internal counter state.... we are tracking total number of standard/critical updates per client.
            obj = self.get_perdevicestate_for_client_id(client_id)
            obj.client_name = client_name
            if is_crit:
                obj.critical_patch_count += update_count
            else:
                obj.standard_patch_count += update_count

        ru = df.groupby(["Update_platform", "Update_critical"], as_index=False)["Update_name"].count()
        for i in ru.to_numpy():
            platform_name = platform_mapping[i[0]]
            is_crit = i[1]
            update_count = i[2]
            software_updates_by_platform.labels(platform_name, is_crit).set(update_count)
