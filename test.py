from fwrest import FWRestQuery
import json
import sys
import os
import pandas as pd
import unittest

from application import ApplicationQueryManager, ApplicationUsageRollup
import test_queries
from test_queries import test_query_app_adobe_acrobat_reader_win, test_win_app_generic_should_not_load, test_query_app_wrong_group_zoom_win, test_query_app_zoom_win
pd.set_option('display.precision', 3)
pd.set_option('display.expand_frame_repr', False)


class FakeRequest:
    def __init__(self, string_data):
        self.data = string_data

    def json(self):
        return json.loads(self.data)


class FakeQueryInteface:
    TEST_QUERY_APPS = 1

    def get_all_inventory_queries(self):
        # returns some good, some bad... some in our group, some not.
        text_queries = [test_query_app_adobe_acrobat_reader_win, 
                test_win_app_generic_should_not_load, 
                test_query_app_wrong_group_zoom_win, 
                test_query_app_zoom_win]

        return [json.loads(t) for t in text_queries]

    def get_results_for_query_id(self, query_id):
        if query_id == FakeQueryInteface.TEST_QUERY_APPS:
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
                "filter_results": 1,
                "total_results": 1,
                "version": 1
            }''')


fw_query = FakeQueryInteface()


class ExtraMetricsFakeQueryTestCase(unittest.TestCase):
    pass


class ExtraMetricsTestCase(unittest.TestCase):
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
            "display_name": "extra metrics - software patch"
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


if __name__ == "__main__":
    unittest.main()
