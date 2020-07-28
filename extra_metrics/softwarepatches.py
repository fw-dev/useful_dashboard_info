from prometheus_client import Gauge
import pandas as pd
import datetime
from datetime import timezone
from extra_metrics.logs import logger

software_updates_by_state = Gauge('extra_metrics_software_updates_by_state',
    'buckets of all the software updates by state - the value is the number of devices in each state, this includes completed updates',
    ["state"])

software_updates_by_critical = Gauge('extra_metrics_software_updates_by_critical',
    'lists all the updates, indicating the number of normal vs critical updates currently known by the server',
    ["platform", "is_critical"])

software_updates_by_popularity = Gauge('extra_metrics_software_updates_by_popularity',
    'list of software updates and the number of devices still needing the update (unassigned), completed updates are not included in this count',
    ["update_name", "update_id", "state"])

software_updates_by_age = Gauge('extra_metrics_software_updates_by_age',
    'list of software updates and their age in days, all updates including completed ones are included here.  The value of the metric is the age in days (from now)',
    ["update_name", "update_id", "created_date"])

software_updates_remaining_by_device = Gauge('extra_metrics_software_updates_remaining_by_device',
    'list of devices and the number of [critical] updates they have remaining to be installed, completed updates are not included in this count',
    ["device_name", "device_id", "is_update_critical"])


class PatchStateCounts:
    def __init__(self):
        self.unassigned = 0
        self.error = 0
        self.warning = 0
        self.assigned = 0
        self.remaining = 0
        self.completed = 0

    def total(self):
        return self.assigned

    def total_assigned_and_unassigned(self):
        return self.assigned + self.unassigned

    def validate_sanity_of_numbers(self):
        assert self.assigned == self.error + self.warning + self.remaining + self.completed

    def total_not_completed(self):
        return self.total() - self.completed


class PerDevicePatchState:
    def __init__(self, client_id):
        self.client_id = client_id
        self.client_name = None
        self.count_crits = PatchStateCounts()
        self.count_normal = PatchStateCounts()

    def get_counter(self, is_update_critcal):
        if is_update_critcal:
            return self.count_crits
        return self.count_normal


class SoftwarePatchStatus:
    def __init__(self, fw_query):
        self.fw_query = fw_query
        # a dictionary of the PerDevicePatchState
        self.state_by_device = {}

    def reset_perdevice_state(self):
        self.state_by_device = {}

    def get_perdevice_counters(self, client_id, is_update_critical):
        return self.get_perdevice_state(client_id).get_counter(is_update_critical)

    def get_perdevice_state(self, client_id):
        if client_id not in self.state_by_device:
            self.state_by_device[client_id] = PerDevicePatchState(client_id)
        return self.state_by_device.get(client_id, None)

    def apply_unassigned_counts_to_perdevice_state(self, devices_dict, is_update_critical):
        for cid in devices_dict["device_ids"]:
            self.get_perdevice_counters(cid, is_update_critical).unassigned += 1

    def apply_assigned_counts_to_perdevice_state(self, assigned_dict, is_update_critical):
        for cid in assigned_dict["completed"]["device_ids"]:
            self.get_perdevice_counters(cid, is_update_critical).completed += 1
        for cid in assigned_dict["remaining"]["device_ids"]:
            self.get_perdevice_counters(cid, is_update_critical).remaining += 1
        for cid in assigned_dict["assigned"]["device_ids"]:
            self.get_perdevice_counters(cid, is_update_critical).assigned += 1
        for cid in assigned_dict["warning"]["device_ids"]:
            self.get_perdevice_counters(cid, is_update_critical).warning += 1
        for cid in assigned_dict["error"]["device_ids"]:
            self.get_perdevice_counters(cid, is_update_critical).error += 1

    def collect_patch_data_status(self):
        j = self.fw_query.get_software_updates_web_ui_j()
        if j is None:
            return

        if "results" not in j or len(j["results"]) == 0:
            logger.info("no results for software update patch status received from FileWave server")
            return None

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
        '''

        columns = [
            "update_name",
            "update_id",
            "update_pk",
            "creation_date",
            "age_in_days",
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

        now = datetime.datetime.now(timezone.utc)

        self.reset_perdevice_state()

        '''
        IMPORTANT:
        assigned_devices:
        - all states EXCEPT assigned under this are mutually exclusive, count_requested is the complete total.
        - is_completed = num_requested > 0 and num_unassigned == 0 and num_remaining == 0
        '''

        for item in res:
            update_id = item['update_id']
            update_pk = item['id']
            acc = item["assigned_devices"]
            update_name = item["name"]
            creation_date = item["creation_date"]
            platform = item["platform"]
            if platform == "macOS" or platform == "0":
                update_name += f" ({update_id})"

            is_critical = item["critical"]
            num_requested = item["count_requested"]
            num_unassigned = item["unassigned_devices"]["count"]
            num_remaining = acc["remaining"]["count"]
            num_assigned = acc["assigned"]["count"]
            num_completed = acc["completed"]["count"]
            num_warning = acc["warning"]["count"]
            num_error = acc["error"]["count"]
            is_completed = num_requested > 0 and num_unassigned == 0 and num_remaining == 0

            self.apply_unassigned_counts_to_perdevice_state(item["unassigned_devices"], is_critical)
            self.apply_assigned_counts_to_perdevice_state(acc, is_critical)

            age_in_days = 99
            if creation_date is not None:
                try:
                    date_value = datetime.datetime.strptime(creation_date, '%Y-%m-%dT%H:%M:%S%z')
                except ValueError:
                    date_value = datetime.datetime.strptime(creation_date, '%Y-%m-%dT%H:%M:%S.%f%z')
                delta = now - date_value
                age_in_days = delta.days

            values.append([
                update_name,
                update_id,
                update_pk,
                creation_date,
                age_in_days,
                is_critical,
                platform,
                num_requested,
                num_unassigned,
                num_assigned,
                num_completed,
                num_remaining,
                num_warning,
                num_error,
                is_completed
            ])

        df = pd.DataFrame(values, columns=columns)

        platform_mapping = {
            "0": "macOS",
            "1": "Microsoft"
        }

        # for platform/criticality
        df_crit = df.groupby(['platform', 'critical'])
        for key, item in df_crit:
            platform_str = key[0]
            if platform_str in platform_mapping:
                platform_str = platform_mapping[platform_str]
            is_crit = key[1]
            total_count = item['update_id'].count()
            software_updates_by_critical.labels(platform_str, is_crit).set(total_count)

        # calculate the outstanding updates, e.g. patches with highest number of clients outstanding, which is:
        #       unassigned + assigned + remaining
        # df_not_completed = df.loc[df['is_completed'] == False]
        per_update_totals = df.groupby(["update_name", "update_pk"], as_index=False)
        for key, item in per_update_totals:
            update_name = key[0]
            update_pk = str(key[1])
            num_not_started = item['unassigned'].sum()
            num_outstanding = item['remaining'].sum()
            num_completed = item['completed'].sum()
            num_with_error_or_warning = item['warning'].sum() + item['error'].sum()

            # print(f"update: {update_name} / {update_pk}, in progress: {num_outstanding}")
            software_updates_by_popularity.labels(update_name, update_pk, "Not Started").set(num_not_started)
            software_updates_by_popularity.labels(update_name, update_pk, "In Progress").set(num_outstanding)
            software_updates_by_popularity.labels(update_name, update_pk, "Completed").set(num_completed)
            software_updates_by_popularity.labels(update_name, update_pk, "Errors/Warnings").set(num_with_error_or_warning)

            software_updates_by_age.labels(update_name, update_pk, item['creation_date']).set(item['age_in_days'])

        t = df.sum(0, numeric_only=True)

        # total number of devices requesting software...
        software_updates_by_state.labels('Requested').set(t['requested'])
        # total number not assigned to any device, even though its requested
        software_updates_by_state.labels('Unassigned').set(t['unassigned'])
        # breakdown of totals for patches that have been assigned...
        # assigned -> remaining (installing) -> completed
        #          -> error|warning
        software_updates_by_state.labels('Assigned').set(t['assigned'])
        software_updates_by_state.labels('Remaining').set(t['remaining'])
        software_updates_by_state.labels('Completed').set(t['completed'])
        software_updates_by_state.labels('Warning').set(t['warning'])
        software_updates_by_state.labels('Error').set(t['error'])

        self.collect_patch_data_per_device()

        return j

    def collect_patch_data_per_device(self):
        j = self.fw_query.get_client_info_j()
        if j is None:
            logger.warning("No info returned from the get_client_info_j query - thats not good")
            return

        if "values" not in j or len(j["values"]) == 0:
            logger.info("no results for software update patch status per device received from FileWave server")
            return None

        if "fields" not in j:
            logger.info("no fields meta data for software update patch status per device received from FileWave server")
            return None

        # use a list of devices, pick up the data from the software update / patching module and fill 
        # in the metric.
        df = pd.DataFrame(j["values"], columns=j["fields"])
        ru = df.groupby(["Client_filewave_client_name", "Client_filewave_id"], as_index=False)
        for key, item in ru:
            client_name = key[0]
            client_id = int(key[1])

            obj = self.get_perdevice_state(client_id)
            obj.client_name = client_name
            # gets the critical patch count
            per_device_critical = obj.get_counter(True)
            # gets the non-critical patch count
            per_device_normal = obj.get_counter(False)

            logger.info(f"patches, device: {client_name}/{client_id}, critical: {per_device_critical.total()}, normal: {per_device_normal.total()}")

            software_updates_remaining_by_device.labels(client_name, client_id, True).set(per_device_critical.total_assigned_and_unassigned())
            software_updates_remaining_by_device.labels(client_name, client_id, False).set(per_device_normal.total_assigned_and_unassigned())
