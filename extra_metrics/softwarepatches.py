from prometheus_client import Gauge
import pandas as pd
from extra_metrics.logs import logger

software_updates_by_state = Gauge('extra_metrics_software_updates_by_state',
    'buckets of all the software updates by state - the value is the number of devices in each state, this includes completed updates',
    ["state"])  

software_updates_by_popularity = Gauge('extra_metrics_software_updates_by_popularity',
    'list of software updates and the number of devices still needing the update (unassigned), completed updates are not included in this count',
    ["update_name", "update_id"])

software_updates_by_platform = Gauge('extra_metrics_software_updates_by_platform',
    'list of platforms and the number of [critical] updates they have available, completed updates are not included in this count',
    ["platform_name", "is_update_critical"])

software_updates_by_device = Gauge('extra_metrics_software_updates_by_device',
    'list of devices and the number of [critical] updates they need to have installed, completed updates are not included in this count',
    ["device_name", "device_id", "is_update_critical"])


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

        # here: device_id references generic_client

        values = [
        ]

        '''
        source information:
        1. every update, with Id references to state of clients in sub-lists

        {
            "id": 174,
            "unique_hash": "2-d9094dcca7459cbd5f50bdca34c20646",
            "name": "macOS Catalina 10.15.5 Update",
            "update_id": "001-12343",
            "version": " ",
            "platform": "0",
            "size": 4755504063,
            "install_size": 4755504063,
            "critical": false,
            "reboot": true,
            "approved": false,
            "automatic": false,
            "creation_date": "2020-05-28T21:34:59+02:00",
            "metadata": {},
            "import_error": null,
            "import_status": 3,
            "count_requested": 1,
            "unassigned_devices": {
                "count": 0,
                "device_ids": []
            },
            "assigned_devices": {
                "assigned": {
                    "count": 1,
                    "device_ids": [
                        11
                    ]
                },
                "warning": {
                    "count": 0,
                    "device_ids": []
                },
                "remaining": {
                    "count": 0,
                    "device_ids": []
                },
                "completed": {
                    "count": 1,
                    "device_ids": [
                        11
                    ]
                },
                "error": {
                    "count": 0,
                    "device_ids": []
                }
            }
        }

        for a SU - completed is:
            [requested] count_requested > 0
            unassigned_devices.count == 0
            [critical]
            [completed] =
                assigned_devices.remaining == 0
                           -or-
                assigned_device.completed = count_requested

        '''

        columns = [
            "update_name",
            "update_id",
            "critical",
            "platform",
            "requested",
            "unassigned",
            "assigned",
            "completed",
            "remaining",
            "warning",
            "error",
            "is_completed"
        ]

        res = j["results"]
        for item in res:
            update_id = item['update_id']
            self.state_by_patch[update_id] = item

            acc = item["assigned_devices"]

            update_name = item["name"]
            platform = item["platform"]
            if platform == "macOS":
                update_name += f" ({update_id})"

            is_critical = item["critical"]
            num_requested = item["count_requested"]
            num_unassigned = item["unassigned_devices"]["count"]
            num_remaining = acc["remaining"]["count"]
            is_completed = num_requested > 0 and num_unassigned == 0 and num_remaining == 0

            values.append([
                update_name,
                update_id,
                is_critical,
                platform,
                num_requested,
                num_unassigned,
                acc["assigned"]["count"],
                acc["completed"]["count"],
                num_remaining,
                acc["warning"]["count"],
                acc["error"]["count"],
                is_completed
            ])

        df = pd.DataFrame(values, columns=columns)
        df_not_completed = df.loc[df['is_completed'] == False]
        per_update_totals = df_not_completed.groupby(["update_name", "update_id"], as_index=False)["unassigned"].sum()
        for item in per_update_totals.to_numpy():
            update_name = item[0]
            update_id = item[1]
            number_of = item[2]
            software_updates_by_popularity.labels(update_name, update_id).set(number_of)

        # number of devices using software updates, grouped by state

        df_sum = df.loc[df['is_completed']]
        sum_completed = df_sum['is_completed'].sum()
        logger.info(f"completed: {sum_completed}")
        software_updates_by_state.labels('Completed').set(sum_completed)

        t = df_not_completed.sum(0, numeric_only=True)
        software_updates_by_state.labels('Remaining').set(t['remaining'])
        software_updates_by_state.labels('Requested').set(t['requested'])
        software_updates_by_state.labels('Unassigned').set(t['unassigned'])
        software_updates_by_state.labels('Assigned').set(t['assigned'])
        software_updates_by_state.labels('Warning').set(t['warning'])
        software_updates_by_state.labels('Error').set(t['error'])

        return j

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

        # this is just a list of the avail patches, this data does not yet
        # tell us if the patch has been installed on the device.
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
