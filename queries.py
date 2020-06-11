query_win_applications = '''
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
            "column": "device_id",
            "component": "Client"
        },
        {
            "column": "device_name",
            "component": "Client"
        }
    ],
    "main_component": "Application",
    "display_name": "extra metrics - win applications"
}
'''

query_client_info = '''{
    "criteria": {
        "expressions": [
            {
                "column": "filewave_id",
                "component": "Client",
                "operator": "!=",
                "qualifier": null
            },
            {
                "column": "archived",
                "component": "Client",
                "operator": "=",
                "qualifier": null
            }
        ],
        "logic": "all"
    },
    "fields": [
        {
            "column": "device_name",
            "component": "Client"
        },
        {
            "column": "filewave_client_locked",
            "component": "Client"
        },
        {
            "column": "free_disk_space",
            "component": "Client"
        },
        {
            "column": "device_id",
            "component": "Client"
        },
        {
            "column": "is_tracking_enabled",
            "component": "Client"
        },
        {
            "column": "location",
            "component": "Client"
        },
        {
            "column": "serial_number",
            "component": "Client"
        },
        {
            "column": "filewave_client_version",
            "component": "DesktopClient"
        },
        {
            "column": "management_mode",
            "component": "Client"
        },
        {
            "column": "filewave_client_name",
            "component": "Client"
        },
        {
            "column": "filewave_id",
            "component": "Client"
        },
        {
            "column": "version",
            "component": "OperatingSystem"
        },
        {
            "column": "enrollment_state",
            "component": "Client"
        },
        {
            "column": "name",
            "component": "OperatingSystem"
        },
        {
            "column": "edition",
            "component": "OperatingSystem"
        },
        {
            "column": "build",
            "component": "OperatingSystem"
        },
        {
            "column": "type",
            "component": "OperatingSystem"
        },
        {
            "column": "last_check_in",
            "component": "Client"
        },
        {
            "column": "filewave_model_number",
            "component": "DesktopClient"
        },
        {
            "column": "device_manufacturer",
            "component": "DesktopClient"
        },
        {
            "column": "last_logged_in_username",
            "component": "Client"
        },
        {
            "column": "device_product_name",
            "component": "Client"
        },
        {
            "column": "current_upstream_host",
            "component": "Client"
        },
        {
            "column": "current_upstream_port",
            "component": "Client"
        },
        {
            "column": "total_disk_space",
            "component": "Client"
        }

    ],
    "main_component": "Client",
    "display_name": "extra metrics - client info"
}
'''

query_software_patches = '''{
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
            "column": "name",
            "component": "Update"
        },
        {
            "column": "update_id",
            "component": "Update"
        },
        {
            "column": "version",
            "component": "Update"
        },
        {
            "column": "platform",
            "component": "Update"
        },
        {
            "column": "critical",
            "component": "Update"
        }
    ],
    "main_component": "Update",
    "display_name": "extra metrics - software patch"
}'''
