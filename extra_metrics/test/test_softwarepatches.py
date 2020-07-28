import unittest
from unittest.mock import MagicMock
from extra_metrics.package import get_package_resource_json
from extra_metrics.test.fake_mocks import FakeQueryInterface
from extra_metrics.softwarepatches import SoftwarePatchStatus
from prometheus_client import REGISTRY


class TestEval21SoftwarePatch(unittest.TestCase):
    def setUp(self):
        self.client_data = get_package_resource_json("extra_metrics.test", "client-software-update-testdata.json")
        self.assertIsNotNone(self.client_data, "the constructor failed to load the client package data for testing")

        self.json_data = get_package_resource_json("extra_metrics.test", "eval21_sware_data.json")
        self.assertIsNotNone(self.json_data, "the constructor failed to load the eval21_sware_data for testing")
        self.fw_query = FakeQueryInterface()

    def test_that_software_patch_data_totals_are_correct(self):
        self.fw_query.get_software_updates_web_ui_j = MagicMock(return_value=self.json_data)
        self.fw_query.get_client_info_j = MagicMock(return_value=self.client_data)
        mgr = SoftwarePatchStatus(self.fw_query)
        mgr.collect_patch_data_status()


class TestSoftwarePatchFetching(unittest.TestCase):
    def setUp(self):
        self.json_data = get_package_resource_json("extra_metrics.test", "software-update-testdata.json")
        self.assertIsNotNone(self.json_data, "the constructor failed to load the web su package data for testing")

        self.client_data = get_package_resource_json("extra_metrics.test", "client-software-update-testdata.json")
        self.assertIsNotNone(self.client_data, "the constructor failed to load the client package data for testing")

        self.fw_query = FakeQueryInterface()

    def test_that_zero_data_doesnt_cause_bad_things(self):
        mgr = SoftwarePatchStatus(self.fw_query)
        mgr.collect_patch_data_status()

    def test_that_software_patch_data_totals_are_correct(self):
        self.fw_query.get_software_updates_web_ui_j = MagicMock(return_value=self.json_data)
        self.fw_query.get_client_info_j = MagicMock(return_value=self.client_data)
        mgr = SoftwarePatchStatus(self.fw_query)
        data = mgr.collect_patch_data_status()

        # for i in data["results"]:
        #     c = i["assigned_devices"]["assigned"]["count"]
        #     if c > 0:
        #         print(c)

        self.assertIsNotNone(data, "the collect_patch_data_status should have got some data to work with")

        # lets have a look at the registry to see if this went well...
        after = REGISTRY.get_sample_value('extra_metrics_software_updates_by_state', labels={"state": "Completed"})
        self.assertEqual(after, 8, "the number of Completed software updates is incorrect")

        after = REGISTRY.get_sample_value('extra_metrics_software_updates_by_state', labels={"state": "Remaining"})
        self.assertEqual(after, 12, "the number of Remaining software updates is incorrect")

        after = REGISTRY.get_sample_value('extra_metrics_software_updates_by_state', labels={"state": "Error"})
        self.assertEqual(after, 10, "the number of Error software updates is incorrect")

        after = REGISTRY.get_sample_value('extra_metrics_software_updates_by_state', labels={"state": "Warning"})
        self.assertEqual(after, 5, "the number of Warning software updates is incorrect")

        after = REGISTRY.get_sample_value('extra_metrics_software_updates_by_state', labels={"state": "Assigned"})
        self.assertEqual(after, 19, "the number of Assigned software updates is incorrect")

        after = REGISTRY.get_sample_value('extra_metrics_software_updates_by_state', labels={"state": "Unassigned"})
        self.assertEqual(after, 175, "the number of Unassigned software updates is incorrect")

        after = REGISTRY.get_sample_value('extra_metrics_software_updates_by_popularity',
                                          labels={"update_name": "iTunes Device Support Update (041-88833)",
                                                  "update_id": "3", "state": "Not Started"})
        self.assertEqual(after, 2, "iTunes Device Support Update should report in progress of 2 units")

        # go to devices 1 & 8 - they should indicate appropriate counts of not-started
        device = mgr.get_perdevice_state(7)
        self.assertEqual(device.get_counter(False).remaining, 4)

        # TODO: pick out a device and check it has the right number of outstanding updates...
