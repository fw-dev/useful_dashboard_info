import unittest
from extra_metrics.fwrest import FWRestQuery
from extra_metrics.config import read_config_helper
from unittest.mock import Mock, patch
import json


class FWQueryTestCase(unittest.TestCase):
    def test_query_init(self):
        fq = FWRestQuery("a", "b")
        self.assertEqual(fq.hostname, "a")
        self.assertEqual(fq.api_key, "b")

    def test_auth_headers_include_api_key_and_json(self):
        fq = FWRestQuery("a", "b")
        d = fq._auth_headers()
        self.assertEqual("b", d['Authorization'])
        self.assertEqual("application/json", d['Content-Type'])

    def test_query_inventory_stub(self):
        fq = FWRestQuery("a", "b")
        self.assertEqual("https://a:20445/inv/api/v1/def",
                         fq.inventory_query_str("def"))
        self.assertEqual("https://a/api/xyz", fq.web_query_str("xyz"))

    def test_version_comparison(self):
        fq = FWRestQuery("a", "b")
        fq.major_version = 10
        fq.minor_version = 9
        fq.patch_version = 8

        # yes; its at least 10.9.8
        self.assertTrue(fq.is_version_at_least(10, 9, 8))

        # no; it's not at least 10.9.9 (patch version here is +1)
        self.assertFalse(fq.is_version_at_least(10, 9, 9))
        # no; its not at least 10.10.8 (minor version is higher)
        self.assertFalse(fq.is_version_at_least(10, 10, 8))
        # no; its not at least 11.9.8 (major version is higher)
        self.assertFalse(fq.is_version_at_least(11, 9, 8))

        # testing that the server is capable or more than... 10.9.7
        self.assertTrue(fq.is_version_at_least(10, 9, 7))  # yeah, the patch version is +1
        self.assertTrue(fq.is_version_at_least(10, 8, 8))  # yeah, it's 10.9
        self.assertTrue(fq.is_version_at_least(9, 9, 8))  # yeah, its 10.

        # this checks the scenario that we released a major revision above what is being checked for
        self.assertTrue(fq.is_version_at_least(9, 10, 8))
        self.assertTrue(fq.is_version_at_least(9, 18, 8))
        self.assertTrue(fq.is_version_at_least(9, 9, 8))
        self.assertTrue(fq.is_version_at_least(4, 4, 4))

    def test_uri_strings_for_pre_14_2_0(self):
        fq = FWRestQuery("a", "b")
        # scenarios: the code is new, but its an OLD server
        fq.hostname = "test"
        fq.major_version = 14
        fq.minor_version = 0
        fq.patch_version = 2
        self.assertEqual('https://test/api/reports/groups_tree', fq.endpoint_groups_tree())
        self.assertEqual('https://test/api/reports/groups/', fq.endpoint_reports_groups())
        self.assertEqual('https://test/api/updates/extended_list/?limit=10000', fq.endpoint_web_software_update())

    def test_uri_strings_for_post_14_2_0(self):
        fq = FWRestQuery("a", "b")
        fq.hostname = "test"
        fq.major_version = 14
        fq.minor_version = 2
        fq.patch_version = 0
        self.assertEqual('https://test/api/reports/v1/groups-tree', fq.endpoint_groups_tree())
        self.assertEqual('https://test/api/reports/v1/groups', fq.endpoint_reports_groups())
        self.assertEqual('https://test/api/updates/v1/extended-list?limit=10000', fq.endpoint_web_software_update())

    @patch('extra_metrics.fwrest.requests.get')
    def test_no_reply_causes_get_version_to_throw_exception(self, mock_get):
        mock_get.return_value.ok = True
        fq = FWRestQuery("a", "b")
        self.assertRaises(Exception, fq.get_current_fw_version_major_minor_patch)

    @patch('extra_metrics.fwrest.requests.get')
    def test_reply_can_be_parsed(self, mock_get):
        json_reply = {'app_version': "12.4.5-1cbfgg"}
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = json_reply

        fq = FWRestQuery("a", "b")
        (major, minor, patch) = fq.get_current_fw_version_major_minor_patch()
        self.assertEqual(12, major)
        self.assertEqual(4, minor)
        self.assertEqual(5, patch)

    @patch('extra_metrics.fwrest.requests.get')
    def test_bad_response_returns_null(self, mock_get):
        json_reply = {'app_version': ""}
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = json_reply

        fq = FWRestQuery("a", "b")
        (major, minor, patch) = fq.get_current_fw_version_major_minor_patch()
        self.assertIsNone(major)
        self.assertIsNone(minor)
        self.assertIsNone(patch)

    def test_endpoint_for_query_definitions(self):
        fq = FWRestQuery("a", "b")
        value = fq.endpoint_inventory_query_definition(12)
        self.assertEqual("https://a:20445/inv/api/v1/query/12", value)

    def test_endpoint_for_query_results(self):
        fq = FWRestQuery("a", "b")
        value = fq.endpoint_inventory_query_results(12)
        self.assertEqual("https://a:20445/inv/api/v1/query_result/12", value)

    def test_checking_status_for_200(self):
        # really, the only this is if we have a 401, we want to throw...
        resp = Mock(status_code=401)
        fq = FWRestQuery("a", "b")
        self.assertRaises(Exception, fq._check_status, resp, "i_am_a_test_method")

    @patch('extra_metrics.fwrest.requests.get')
    def test_getting_query_definition(self, mock_get):
        mock_get.return_value = Mock(status_code=200)
        mock_get.return_value.json.return_value = "{abc}"
        fq = FWRestQuery("a", "b")
        value = fq.get_definition_for_query_id_j(555)
        self.assertEqual("{abc}", value)

        mock_get.return_value.status_code = 350
        self.assertIsNone(fq.get_definition_for_query_id_j(333))

    @patch('extra_metrics.fwrest.requests.get')
    def test_getting_results_for_query_id(self, mock_get):
        mock_get.return_value = Mock(status_code=200)
        mock_get.return_value.json.return_value = "{abc}"
        fq = FWRestQuery("a", "b")
        value = fq.get_results_for_query_id(555)
        self.assertEqual(value.status_code, 200)
        self.assertEqual("{abc}", value.json())

    @patch('extra_metrics.fwrest.requests.get')
    def test_finding_group_by_name_success(self, mock_get):
        json_for_success = '{ "groups_hierarchy": [ { "name": "bob" }, { "name": "tim" }, { "name": "nobody" } ] }'     
        mock_get.return_value = Mock(status_code=200)
        mock_get.return_value.json.return_value = json.loads(json_for_success)

        # test we can find bob, tim and nobody
        fq = FWRestQuery("a", "b")
        self.assertIsNotNone(fq.find_group_with_name("bob"))
        self.assertIsNotNone(fq.find_group_with_name("tim"))
        self.assertIsNotNone(fq.find_group_with_name("nobody"))
        self.assertIsNone(fq.find_group_with_name("jason"))

    @patch('extra_metrics.fwrest.requests.get')
    def test_finding_group_by_name_fails_with_bad_response(self, mock_get):
        mock_get.return_value = Mock(status_code=205)  # anything other than 200
        fq = FWRestQuery("a", "b")
        self.assertIsNone(fq.find_group_with_name("bob"))

