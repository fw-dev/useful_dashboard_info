import pkg_resources
import json


def get_package_resource_string(package_path, filename):
    return pkg_resources.resource_string(package_path, filename)


def get_package_resource_json(package_path, filename):
    return json.loads(get_package_resource_string(package_path, filename).decode('utf-8'))
