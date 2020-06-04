
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
    "main_component": "Update"
}'''

query_client_info = '''{
  "criteria": {
    "column": "filewave_id",
    "component": "Client",
    "operator": "!=",
    "qualifier": null
  },
  "fields": [
    {
      "column": "device_name",
      "component": "Client"
    },
    {
      "column": "filewave_id",
      "component": "Client"
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
      "column": "name",
      "component": "OperatingSystem"
    },
    {
      "column": "version",
      "component": "OperatingSystem"
    },
    {
      "column": "last_check_in",
      "component": "Client"
    },
    {
      "column": "edition",
      "component": "OperatingSystem"
    },
    {
      "column": "enrollment_state",
      "component": "Client"
    },
    {
      "column": "serial_number",
      "component": "Client"
    },
    {
      "column": "management_mode",
      "component": "Client"
    },
    {
      "column": "current_ip_address",
      "component": "Client"
    },
    {
      "column": "is_tracking_enabled",
      "component": "Client"
    }
  ],
  "main_component": "Client"
}
'''
