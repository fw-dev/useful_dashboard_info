from prometheus_client import Gauge
import pandas as pd
import datetime
from datetime import timezone
from extra_metrics.compliance import ClientCompliance
from extra_metrics.logs import logger

device_checkin_days = Gauge('extra_metrics_devices_by_checkin_days',
                            'various interesting stats on a per device basis, days since checked, compliance status',
                            ["days", ])

device_client_modelnumber = Gauge('extra_metrics_per_device_modelnum',
                           'provides a value of the model number per device',
                           ["device_name"])

device_client_compliance = Gauge('extra_metrics_per_device_compliance',
                           'provides a value of the compliance state per device, used for device health graph',
                           ["compliance"])

device_client_version = Gauge('extra_metrics_per_device_client_version',
                           'number of devices rolled up by client version',
                           ["fw_client_version"])

device_client_platform = Gauge('extra_metrics_per_device_platform',
                           'number of devices rolled up by platform',
                           ["platform"])

device_client_tracked = Gauge('extra_metrics_per_device_tracked',
                           'number of devices being tracked',
                           ["tracked"])

device_client_locked = Gauge('extra_metrics_per_device_locked',
                           'number of devices locked',
                           ["locked"])


class PerDeviceStatus:
    def __init__(self, fw_query):
        self.fw_query = fw_query

    def _rollup_by_single_column_count_client_filewave_id(self, df, column_name):
        return df.groupby([column_name], as_index=False)["Client_filewave_id"].count()

    def _set_metric_pair(self, metric, item):
        label_value = item[0]
        total_count = item[1]
        metric.labels(label_value).set(total_count)
        return (label_value, total_count)

    def collect_client_data(self, soft_patches):
        Client_device_name = 0
        Client_free_disk_space = 2
        Client_filewave_id = 10
        Client_last_check_in = 17
        DesktopClient_filewave_model_number = 18
        Client_total_disk_space = 24

        j = self.fw_query.get_client_info_j()

        try:
            assert j["fields"]
            assert j["fields"][Client_device_name] == "Client_device_name", "field 0 is expected to be the Client's name"
            assert j["fields"][Client_last_check_in] == "Client_last_check_in", "field 17 is expected to be the Client's last check in date/time"
            assert j["fields"][Client_filewave_id] == "Client_filewave_id", "field 10 is expected to be the Client's filewave_id"

            buckets = [0, 0, 0, 0]
            now = datetime.datetime.now()

            df = pd.DataFrame(j["values"], columns=j["fields"])

            # devices by client_version
            for item in self._rollup_by_single_column_count_client_filewave_id(df, "DesktopClient_filewave_client_version").to_numpy():
                version = item[0]
                total_count = item[1]
                if version is None:
                    version = "Not Reported"
                device_client_version.labels(version).set(total_count)
                logger.info(f"device client version: {version}, {total_count}")

            # roll up devices per platform
            for item in self._rollup_by_single_column_count_client_filewave_id(df, "OperatingSystem_name").to_numpy():
                (a, b) = self._set_metric_pair(device_client_platform, item)
                logger.info(f"device platform: {a}, {b}")

            # roll up devices by 'tracking enabled' or not
            for item in self._rollup_by_single_column_count_client_filewave_id(df, "Client_is_tracking_enabled").to_numpy():
                (a, b) = self._set_metric_pair(device_client_tracked, item)
                logger.info(f"device by tracking: {a}, {b}")

            # and by locked state
            for item in self._rollup_by_single_column_count_client_filewave_id(df, "Client_filewave_client_locked").to_numpy():
                (a, b) = self._set_metric_pair(device_client_locked, item)
                logger.info(f"device by locked: {a}, {b}")

            # a bit of logic here, so rollup isn't via pandas...
            device_count_by_compliance = {
                ClientCompliance.STATE_OK: 0,
                ClientCompliance.STATE_ERROR: 0,
                ClientCompliance.STATE_WARNING: 0,
                ClientCompliance.STATE_UNKNOWN: 0,
            }

            for v in j["values"]:
                # if there is no last check in date, we want to assume it's NEVER checked in
                checkin_days = 99
                if v[Client_last_check_in] is not None:
                    checkin_date = datetime.datetime.strptime(
                        v[Client_last_check_in], '%Y-%m-%dT%H:%M:%S.%fZ')
                    delta = now - checkin_date
                    checkin_days = delta.days

                total_crit = 0
                total_normal = 0

                client_fw_id = v[Client_filewave_id]
                if client_fw_id is not None:
                    per_device_state = soft_patches.get_perdevice_state(client_fw_id)
                    if per_device_state is not None:
                        total_crit = per_device_state.get_counter(True).total_not_completed()
                        total_normal = per_device_state.get_counter(False).total_not_completed()

                    device_client_modelnumber.labels(
                        v[Client_device_name]
                    ).set(v[DesktopClient_filewave_model_number] if v[DesktopClient_filewave_model_number] is not None else 0)

                    comp_check = ClientCompliance(
                        v[Client_total_disk_space],
                        v[Client_free_disk_space],
                        checkin_days,
                        total_crit,
                        total_normal
                    )

                    device_count_by_compliance[comp_check.get_compliance_state()] += 1

                if(checkin_days <= 1):
                    buckets[0] += 1
                elif checkin_days < 7:
                    buckets[1] += 1
                elif checkin_days < 30:
                    buckets[2] += 1
                else:
                    buckets[3] += 1

            for key, value in device_count_by_compliance.items():
                device_client_compliance.labels(ClientCompliance.get_compliance_state_str(key)).set(value)

            device_checkin_days.labels('Less than 1').set(buckets[0])
            device_checkin_days.labels('Less than 7').set(buckets[1])
            device_checkin_days.labels('Less than 30').set(buckets[2])
            device_checkin_days.labels('More than 30').set(buckets[3])

        except AssertionError as e1:
            print("The validation/assertions failed: %s" % (e1,))
