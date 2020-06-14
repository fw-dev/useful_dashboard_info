from extra_metrics.fwrest import FWRestQuery

import json
import sys
import os
import pandas as pd
import unittest

from prometheus_client import REGISTRY

from extra_metrics.application import ApplicationQueryManager, ApplicationUsageRollup, app_version_count
from extra_metrics.compliance import ClientCompliance
from extra_metrics.logs import init_logging

from test_queries import *

pd.set_option('display.precision', 3)
pd.set_option('display.expand_frame_repr', False)

# pointless, but who can blame me for wanting to get 100% coverage on my codebase? (and this found a bug!)
init_logging()

class FakeRequest:
    def __init__(self, string_data):
        self.data = string_data

    def json(self):
        return json.loads(self.data)


class FakeQueryInteface:
    TEST_QUERY_APPS = 1

    def __init__(self, create_inventory_callback=None):
        self.create_inventory_callback = create_inventory_callback
        super()

    def create_inventory_query(self, json_obj):
        if self.create_inventory_callback: # pragma: no branch
            self.create_inventory_callback(json_obj)

    def ensure_inventory_query_group_exists(self, name_of_query):
        assert name_of_query is not None
        my_data = '''{
            "name": "%s",
            "parent": %d,
            "id": %d
        }''' % (test_queries.MAIN_GROUP_NAME, test_queries.MAIN_GROUP_PARENT_ID, test_queries.MAIN_GROUP_ID)
        return json.loads(my_data), False

    def get_all_inventory_queries(self):
        # returns some good, some bad... some in our group, some not.
        text_queries = [test_query_app_adobe_acrobat_reader_win,
                        test_win_app_generic_should_not_load,
                        test_query_app_wrong_group_zoom_win,
                        test_query_app_zoom_win]

        return [json.loads(t) for t in text_queries]

    def get_results_for_query_id(self, query_id):
        if query_id == 105:
            return FakeRequest('''{
                "offset": 0,
                "fields": [
                    "Application_product_id",
                    "Application_name",
                    "Application_version",
                    "Application_size",
                    "Application_install_size",
                    "Application_is_validated",
                    "Client_filewave_client_name",
                    "Client_device_id"
                ],
                "values": [
                    [
                        "{abcdefg}",
                        "Some App",
                        "12.1",
                        null,
                        6459167232,
                        null,
                        "hades",
                        "4d9fe4590232f39b783d95adf8b12bb24e4f7139"
                    ],
                    [
                        "{AC76BA86-7AD7-1033-7B44-AC0F074E4100}",
                        "Zoom",
                        "20",
                        null,
                        339167232,
                        null,
                        "hades",
                        "4d9fe4590232f39b783d95adf8b12bb24e4f7139"
                    ],
                    [
                        "{AC76BA86-7AD7-1033-7B44-AC0F074E4100}",
                        "Zoom App",
                        "20.1",
                        null,
                        339167232,
                        null,
                        "hades",
                        "4d9fe4590232f39b783d95bdf8b12bb24e4f7139"
                    ]

                ],
                "filter_results": 3,
                "total_results": 3,
                "version": 1
            }''')

        if query_id == FakeQueryInteface.TEST_QUERY_APPS or query_id == 101:
            return FakeRequest('''{
                "offset": 0,
                "fields": [
                    "Application_product_id",
                    "Application_name",
                    "Application_version",
                    "Application_size",
                    "Application_install_size",
                    "Application_is_validated",
                    "Client_filewave_client_name",
                    "Client_device_id"
                ],
                "values": [
                    [
                        "{abcdefg}",
                        "Some App",
                        "12.1",
                        null,
                        6459167232,
                        null,
                        "hades",
                        "4d9fe4590232f39b783d95adf8b12bb24e4f7139"
                    ],
                    [
                        "{AC76BA86-7AD7-1033-7B44-AC0F074E4100}",
                        "Adobe Acrobat Reader DC",
                        "20.009.20067",
                        null,
                        339167232,
                        null,
                        "hades",
                        "4d9fe4590232f39b783d95adf8b12bb24e4f7139"
                    ],
                    [
                        "{AC76BA86-7AD7-1033-7B44-AC0F074E4100}",
                        "Adobe Acrobat Reader DC",
                        "20.009.20067",
                        null,
                        339167232,
                        null,
                        "hades2",
                        "4d9fe4590232f39b783d95bdf8b12bb24e4f7139"
                    ]

                ],
                "filter_results": 3,
                "total_results": 3,
                "version": 1
            }''')


fw_query = FakeQueryInteface()


class ExtraMetricsQueryTestCase(unittest.TestCase):
    def test_query_init(self):
        fq = FWRestQuery("a", "b")
        self.assertEqual(fq.hostname, "a")
        self.assertEqual(fq.api_key, "b")

    def test_query_inventory_stub(self):
        fq = FWRestQuery("a", "b")
        self.assertEqual("https://a:20445/inv/api/v1/def",
                         fq._fw_run_inv_query("def"))
        self.assertEqual("https://a/api/xyz", fq._fw_run_web_query("xyz"))


class ExtraMetricsTestCase(unittest.TestCase):
    def test_app_manager_rolls_queries_and_populates_metrics(self):
        app_mgr = ApplicationQueryManager(fw_query)
        app_mgr.validate_query_definitions()
        app_mgr.collect_application_query_results()

        after = REGISTRY.get_sample_value('extra_metrics_application_version',
                                          labels={"application_name": "Adobe Acrobat Reader DC", "application_version": "20.009.20067"})
        self.assertEqual(2, after)
        after = REGISTRY.get_sample_value('extra_metrics_application_version',
                                          labels={"application_name": "Some App", "application_version": "12.1"})
        self.assertEqual(1, after)
        after = REGISTRY.get_sample_value('extra_metrics_application_version',
                                          labels={"application_name": "Zoom", "application_version": "20"})
        self.assertEqual(1, after)

    def test_app_manager_query_validation(self):
        app_mgr = ApplicationQueryManager(fw_query)
        self.assertEqual(len(app_mgr.app_queries), 0)
        app_mgr.validate_query_definitions()
        self.assertEqual(len(app_mgr.app_queries), 2)

    def test_app_manager_doesnt_load_crap_queries(self):
        app_mgr = ApplicationQueryManager(fw_query)
        app_mgr.retrieve_all_queries_in_group(test_queries.MAIN_GROUP_ID)
        self.assertEqual(len(app_mgr.app_queries), 2)
        self.assertTrue(120 not in app_mgr.app_queries.keys())
        self.assertTrue(101 in app_mgr.app_queries.keys())
        self.assertTrue(105 in app_mgr.app_queries.keys())

    def test_app_mgr_accepts_valid_inventory_query(self):
        well_formed_query = '''{
            "favorite": true,
            "fields": [
                {
                    "column": "device_id",
                    "component": "Client"
                },
                {
                    "column": "name",
                    "component": "Application"
                },
                {
                    "column": "version",
                    "component": "Application"
                }
            ],
            "main_component": "Update",
            "name": "extra metrics - software patch",
            "id": 55
        }'''

        result = ApplicationQueryManager.is_query_valid(
            json.loads(well_formed_query))
        self.assertTrue(result)

    def test_app_mgr_rejects_invalid_inventory_query(self):
        badly_formed_query = '''{
            "favorite": true,
            "fields": [
                {
                    "column": "filewave_id",
                    "component": "Client"
                },
                {
                    "column": "filewave_client_name",
                    "component": "Client"
                },
                {
                    "column": "version",
                    "component": "Update"
                }
            ],
            "main_component": "Update",
            "name": "extra metrics - software patch"
        }'''

        result = ApplicationQueryManager.is_query_valid(
            json.loads(badly_formed_query))
        self.assertFalse(result)

    def test_app_rollup(self):
        thing = ApplicationUsageRollup(FakeQueryInteface.TEST_QUERY_APPS, [
                                       "Application_name", "Application_version"], "Client_device_id")
        thing.exec(fw_query)

        # examine the rollup results to prove this worked
        r = thing.results()
        self.assertEqual(len(r), 2)

        item = r[0]
        item_name = item[0]
        item_version = item[1]
        item_count = item[2]

        self.assertEqual(item_name, "Adobe Acrobat Reader DC")
        self.assertEqual(item_version, "20.009.20067")
        self.assertEqual(item_count, 2)

        item = r[1]
        item_name = item[0]
        item_version = item[1]
        item_count = item[2]

        self.assertEqual(item_name, "Some App")
        self.assertEqual(item_version, "12.1")
        self.assertEqual(item_count, 1)

    def test_app_mgr_can_create_queries(self):
        loaded_data = []
        def test_query_load(json_data):
            nonlocal loaded_data
            loaded_data.append(json_data)

        my_query = FakeQueryInteface(test_query_load)
        app_mgr = ApplicationQueryManager(my_query)
        app_mgr.create_default_queries_in_group(test_queries.MAIN_GROUP_ID)
        self.assertEqual(9, len(loaded_data))
        # for r in loaded_data:
        #     print(r)


class TestClientComplianceCase(unittest.TestCase):
    def test_compliance_with_no_data(self):
        c = ClientCompliance(None, None, None)
        self.assertEqual(c.get_checkin_compliance(),
                         ClientCompliance.STATE_UNKNOWN)
        self.assertEqual(c.get_disk_compliance(),
                         ClientCompliance.STATE_UNKNOWN)
        self.assertEqual(c.get_compliance_state(),
                         ClientCompliance.STATE_UNKNOWN)

    def test_compliance_checkin_less_than_7_is_ok(self):
        c = ClientCompliance(None, None, 6)
        self.assertEqual(c.get_checkin_compliance(), ClientCompliance.STATE_OK)
        c.last_checkin_days = 7
        self.assertEqual(c.get_checkin_compliance(),
                         ClientCompliance.STATE_WARNING)

    def test_compliance_checkin_less_than_14_is_warning(self):
        c = ClientCompliance(None, None, 13)
        self.assertEqual(c.get_checkin_compliance(),
                         ClientCompliance.STATE_WARNING)
        c.last_checkin_days = 14
        self.assertEqual(c.get_checkin_compliance(),
                         ClientCompliance.STATE_ERROR)

    def test_compliance_disk_space_free_more_than_20pcnt(self):
        # < 20% left is warning
        # < 5% left is critical, or less than 5g
        c = ClientCompliance(100, 25, 3)
        self.assertEqual(c.get_disk_compliance(), ClientCompliance.STATE_OK)
        c = ClientCompliance(100, 20, 3)
        self.assertEqual(c.get_disk_compliance(), ClientCompliance.STATE_OK)

    def test_compliance_disk_space_free_between_5_and_20pcnt(self):
        c = ClientCompliance(100, 5, 3)
        self.assertEqual(c.get_disk_compliance(),
                         ClientCompliance.STATE_WARNING)
        c = ClientCompliance(100, 19, 3)
        self.assertEqual(c.get_disk_compliance(),
                         ClientCompliance.STATE_WARNING)

    def test_compliance_disk_space_free_less_than_5pcnt(self):
        c = ClientCompliance(100, 4.9, 3)
        self.assertEqual(c.get_disk_compliance(), ClientCompliance.STATE_ERROR)

    def test_compliance_value_is_max_of_either(self):
        # enforce that it's max() of either value
        c1 = ClientCompliance(100, 5, 3)  # WARNING for DISK
        c2 = ClientCompliance(100, 40, 500)  # ERROR for CHECKIN DAYS
        self.assertTrue(c2.get_checkin_compliance() > c1.get_disk_compliance())
        self.assertEqual(c2.get_compliance_state(),
                         ClientCompliance.STATE_ERROR)


if __name__ == "__main__":
    unittest.main()
