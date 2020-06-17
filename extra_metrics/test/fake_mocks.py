import json
import pandas as pd

from extra_metrics.test.test_queries import \
    MAIN_GROUP_ID, MAIN_GROUP_NAME, MAIN_GROUP_PARENT_ID

from extra_metrics.test.test_queries import \
    test_query_app_adobe_acrobat_reader_win, \
    test_query_app_wrong_group_zoom_win, \
    test_query_app_zoom_win, \
    test_win_app_generic_should_not_load

pd.set_option('display.precision', 3)
pd.set_option('display.expand_frame_repr', False)


class FakeRequest:
    def __init__(self, string_data):
        self.data = string_data

    def json(self):
        return json.loads(self.data)


class FakeQueryInterface:
    TEST_QUERY_APPS = 1
    TEST_QUERY_DATA_INVALID = 99
    TEST_QUERY_DATA_ALMOST_VALID1 = 98
    TEST_QUERY_DATA_ALMOST_VALID2 = 97

    def __init__(self, create_inventory_callback=None):
        self.create_inventory_callback = create_inventory_callback
        super()

    def get_current_fw_version_major_minor_patch(self):
        raise Exception("not implemented - please mock this")

    def create_inventory_query(self, json_obj):
        if self.create_inventory_callback:  # pragma: no branch
            self.create_inventory_callback(json_obj)

    def get_software_updates_web_ui_j(self):
        t = '''{
            "results": [
            ]
        }'''
        return json.loads(t)

    def ensure_inventory_query_group_exists(self, name_of_query):
        assert name_of_query is not None
        my_data = '''{
            "name": "%s",
            "parent": %d,
            "id": %d
        }''' % (MAIN_GROUP_NAME, MAIN_GROUP_PARENT_ID, MAIN_GROUP_ID)
        return json.loads(my_data), False

    def get_all_inventory_queries(self):
        # returns some good, some bad... some in our group, some not.
        text_queries = [test_query_app_adobe_acrobat_reader_win,
                        test_win_app_generic_should_not_load,
                        test_query_app_wrong_group_zoom_win,
                        test_query_app_zoom_win]

        return [json.loads(t) for t in text_queries]

    def get_definition_for_query_id_j(self, q_id):
        if q_id == FakeQueryInterface.TEST_QUERY_DATA_INVALID:
            return None

        if q_id == FakeQueryInterface.TEST_QUERY_DATA_ALMOST_VALID1:
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
                "main_component": "Update"
                }'''
            return json.loads(badly_formed_query)

        if q_id == FakeQueryInterface.TEST_QUERY_DATA_ALMOST_VALID2:
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
                "name": "this has a name",
                "main_component": "Update"
                }'''
            return json.loads(badly_formed_query)

        if q_id == 66:
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
                "id": 66,
                "name": "extra metrics - software patch"
                }'''
            return json.loads(badly_formed_query)

        if q_id == 55:
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
            return json.loads(well_formed_query)

        all_queries = self.get_all_inventory_queries()
        for a_query in all_queries:
            if a_query["id"] == q_id:
                return a_query
        return None

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
                        "Zoom",
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

        if query_id == FakeQueryInterface.TEST_QUERY_APPS or query_id == 101:
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
                        "Adobe Acrobat Reader DC",
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
