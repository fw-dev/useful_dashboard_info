import unittest
import unittest.mock as mock
from unittest.mock import MagicMock
from prometheus_client import REGISTRY

from extra_metrics.test.fake_mocks import FakeQueryInterface
from extra_metrics.test.test_queries import MAIN_GROUP_ID
from extra_metrics.application import (
    ApplicationQueryManager,
    ApplicationUsageRollup
)


class ExtraMetricsTestCase(unittest.TestCase):
    def setUp(self):
        self.fw_query = FakeQueryInterface()

    def test_app_manager_rolls_queries_and_populates_metrics(self):
        app_mgr = ApplicationQueryManager(self.fw_query)
        app_mgr.validate_query_definitions()
        app_mgr.collect_application_query_results()

        after = REGISTRY.get_sample_value('extra_metrics_application_version',
                                          labels={"query_name": "Adobe Acrobat Reader Win",
                                                  "application_version": "12.1", "query_id": "101"})
        self.assertEqual(1, after)

        after = REGISTRY.get_sample_value('extra_metrics_application_version',
                                          labels={"query_name": "Adobe Acrobat Reader Win",
                                                  "application_version": "20.009.20067", "query_id": "101"})
        self.assertEqual(2, after)

        after = REGISTRY.get_sample_value('extra_metrics_application_version',
                                          labels={"query_name": "Zoom Win", "application_version": "20.1",
                                                  "query_id": "105"})
        self.assertEqual(1, after)

    def test_app_manager_query_validation(self):
        app_mgr = ApplicationQueryManager(self.fw_query)
        self.assertEqual(len(app_mgr.app_queries), 0)
        app_mgr.validate_query_definitions()
        self.assertEqual(len(app_mgr.app_queries), 2)

    def test_app_manager_invalid_query_cannot_validate(self):
        app_mgr = ApplicationQueryManager(self.fw_query)
        self.assertFalse(app_mgr.is_query_valid(
            FakeQueryInterface.TEST_QUERY_DATA_INVALID))
        self.assertFalse(app_mgr.is_query_valid(
            FakeQueryInterface.TEST_QUERY_DATA_ALMOST_VALID1))
        self.assertFalse(app_mgr.is_query_valid(
            FakeQueryInterface.TEST_QUERY_DATA_ALMOST_VALID2))

    def test_app_manager_doesnt_load_crap_queries(self):
        app_mgr = ApplicationQueryManager(self.fw_query)
        app_mgr.retrieve_all_queries_in_group(MAIN_GROUP_ID)
        self.assertEqual(len(app_mgr.app_queries), 2)
        self.assertTrue(120 not in app_mgr.app_queries.keys())
        self.assertTrue(101 in app_mgr.app_queries.keys())
        self.assertTrue(105 in app_mgr.app_queries.keys())

    def test_app_mgr_accepts_valid_inventory_query(self):
        app_mgr = ApplicationQueryManager(self.fw_query)
        result = app_mgr.is_query_valid(55)
        self.assertTrue(result)

    def test_app_mgr_rejects_invalid_inventory_query(self):
        app_mgr = ApplicationQueryManager(self.fw_query)
        result = app_mgr.is_query_valid(66)
        self.assertFalse(result)

    def test_app_rollup(self):
        thing = ApplicationUsageRollup(FakeQueryInterface.TEST_QUERY_APPS, [
            "Application_name", "Application_version"], "Client_device_id")
        thing.exec(self.fw_query)

        # examine the rollup results to prove this worked
        r = thing.results()
        self.assertEqual(len(r), 2)

        item = r[0]
        item_name = item[0]
        item_version = item[1]
        item_count = item[2]

        self.assertEqual(item_name, "Adobe Acrobat Reader DC")
        self.assertEqual(item_version, "12.1")
        self.assertEqual(item_count, 1)

        item = r[1]
        item_name = item[0]
        item_version = item[1]
        item_count = item[2]

        self.assertEqual(item_name, "Adobe Acrobat Reader DC")
        self.assertEqual(item_version, "20.009.20067")
        self.assertEqual(item_count, 2)

    def test_app_mgr_can_create_queries(self):
        loaded_data = []

        def test_query_load(json_data):
            nonlocal loaded_data
            loaded_data.append(json_data)

        my_query = FakeQueryInterface(test_query_load)
        app_mgr = ApplicationQueryManager(my_query)
        app_mgr.create_default_queries_in_group(MAIN_GROUP_ID)

        self.assertEqual(9, len(loaded_data))
