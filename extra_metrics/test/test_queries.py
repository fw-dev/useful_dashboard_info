MAIN_GROUP_ID = 5
MAIN_GROUP_NAME = "I am your Group"
MAIN_GROUP_PARENT_ID = 433

INVALID_GROUP = 55

test_win_app_generic_should_not_load = '''
{
    "criteria": {
        "expressions": [
            {
                "column": "type",
                "component": "OperatingSystem",
                "operator": "is",
                "qualifier": "WIN"
            }
        ],
        "logic": "all"
    },
    "fields": [
        {
            "column": "product_id",
            "component": "Application"
        },
        {
            "column": "name",
            "component": "Application"
        },
        {
            "column": "version",
            "component": "Application"
        },
        {
            "column": "size",
            "component": "Application"
        },
        {
            "column": "install_size",
            "component": "Application"
        },
        {
            "column": "is_validated",
            "component": "Application"
        },
        {
            "column": "device_name",
            "component": "Client"
        }
    ],
    "main_component": "Application",
    "name": "generic query",
    "id": 100,
    "group": %d
}
''' % MAIN_GROUP_ID

test_query_app_adobe_acrobat_reader_win = '''{
    "criteria": {
        "expressions": [
            {
                "column": "name",
                "component": "Application",
                "operator": "is",
                "qualifier": "Adobe Acrobat Reader DC"
            },
            {
                "column": "type",
                "component": "OperatingSystem",
                "operator": "is",
                "qualifier": "WIN"
            }
        ],
        "logic": "all"
    },
    "fields": [
        {
            "column": "product_id",
            "component": "Application"
        },
        {
            "column": "name",
            "component": "Application"
        },
        {
            "column": "version",
            "component": "Application"
        },
        {
            "column": "size",
            "component": "Application"
        },
        {
            "column": "install_size",
            "component": "Application"
        },
        {
            "column": "is_validated",
            "component": "Application"
        },
        {
            "column": "filewave_client_name",
            "component": "Client"
        },
        {
            "column": "device_id",
            "component": "Client"
        }
    ],
    "main_component": "Application",
    "id": 101,
    "group": %d,
    "name": "Adobe Acrobat Reader Win"
}''' % MAIN_GROUP_ID

test_query_app_zoom_win = '''{
    "criteria": {
        "expressions": [
            {
                "column": "name",
                "component": "Application",
                "operator": "is",
                "qualifier": "Zoom"
            },
            {
                "column": "type",
                "component": "OperatingSystem",
                "operator": "is",
                "qualifier": "WIN"
            },
            {
                "column": "version",
                "component": "Application",
                "operator": "contains",
                "qualifier": "."
            }
        ],
        "logic": "all"
    },
    "fields": [
        {
            "column": "product_id",
            "component": "Application"
        },
        {
            "column": "name",
            "component": "Application"
        },
        {
            "column": "version",
            "component": "Application"
        },
        {
            "column": "size",
            "component": "Application"
        },
        {
            "column": "install_size",
            "component": "Application"
        },
        {
            "column": "is_validated",
            "component": "Application"
        },
        {
            "column": "filewave_client_name",
            "component": "Client"
        },
        {
            "column": "device_id",
            "component": "Client"
        }
    ],
    "main_component": "Application",
    "group": %d,
    "id": 105,
    "name": "Zoom Win"
}''' % MAIN_GROUP_ID

test_query_app_wrong_group_zoom_win = '''{
    "criteria": {
        "expressions": [
            {
                "column": "name",
                "component": "Application",
                "operator": "is",
                "qualifier": "Zoom"
            },
            {
                "column": "type",
                "component": "OperatingSystem",
                "operator": "is",
                "qualifier": "WIN"
            },
            {
                "column": "version",
                "component": "Application",
                "operator": "contains",
                "qualifier": "."
            }
        ],
        "logic": "all"
    },
    "fields": [
        {
            "column": "product_id",
            "component": "Application"
        },
        {
            "column": "name",
            "component": "Application"
        },
        {
            "column": "version",
            "component": "Application"
        },
        {
            "column": "size",
            "component": "Application"
        },
        {
            "column": "install_size",
            "component": "Application"
        },
        {
            "column": "is_validated",
            "component": "Application"
        },
        {
            "column": "device_id",
            "component": "Client"
        }
    ],
    "group": %d,
    "main_component": "Application",
    "name": "Zoom Win wrong group",
    "id": 120,
    "favorite": false
}''' % INVALID_GROUP
