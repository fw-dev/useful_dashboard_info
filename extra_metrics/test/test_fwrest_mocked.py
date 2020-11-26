import unittest
from extra_metrics.fwrest import FWRestQuery
from unittest.mock import Mock, patch
import json


class FWRESTTestCaseWithMocks(unittest.TestCase):
    def setUp(self):
        self.fq = FWRestQuery("a", "b")
        self.json_for_success = '{ "groups_hierarchy": [ { "name": "bob" }, { "name": "tim" }, { "name": "nobody" } ] }'     

        self.mock_get_patcher = patch('extra_metrics.fwrest.requests.get')
        self.mock_get = self.mock_get_patcher.start()

    def tearDown(self):
        self.mock_get_patcher.stop()

    def test_no_reply_causes_get_version_to_throw_exception(self):
        self.mock_get.return_value.ok = True
        self.assertRaises(Exception, self.fq.get_current_fw_version_major_minor_patch)

    def test_reply_can_be_parsed(self):
        json_reply = {'app_version': "12.4.5-1cbfgg"}
        self.mock_get.return_value.ok = True
        self.mock_get.return_value.json.return_value = json_reply

        (major, minor, patch) = self.fq.get_current_fw_version_major_minor_patch()
        self.assertEqual(12, major)
        self.assertEqual(4, minor)
        self.assertEqual(5, patch)

    def test_bad_response_returns_null(self):
        json_reply = {'app_version': ""}
        self.mock_get.return_value.ok = True
        self.mock_get.return_value.json.return_value = json_reply

        (major, minor, patch) = self.fq.get_current_fw_version_major_minor_patch()
        self.assertIsNone(major)
        self.assertIsNone(minor)
        self.assertIsNone(patch)

    def test_endpoint_for_query_definitions(self):
        value = self.fq.endpoint_inventory_query_definition(12)
        self.assertEqual("https://a:20445/inv/api/v1/query/12", value)

    def test_endpoint_for_query_results(self):
        value = self.fq.endpoint_inventory_query_results(12)
        self.assertEqual("https://a:20445/inv/api/v1/query_result/12", value)

    def test_checking_status_for_200(self):
        # really, the only this is if we have a 401, we want to throw...
        resp = Mock(status_code=401)
        self.assertRaises(Exception, self.fq._check_status, resp, "i_am_a_test_method")

    def test_getting_query_definition(self):
        self.mock_get.return_value = Mock(status_code=200)
        self.mock_get.return_value.json.return_value = "{abc}"
        value = self.fq.get_definition_for_query_id_j(555)
        self.assertEqual("{abc}", value)
        self.mock_get.return_value.status_code = 350
        self.assertIsNone(self.fq.get_definition_for_query_id_j(333))

    def test_getting_results_for_query_id(self):
        self.mock_get.return_value = Mock(status_code=200)
        self.mock_get.return_value.json.return_value = "{abc}"
        value = self.fq.get_results_for_query_id(555)
        self.assertEqual(value.status_code, 200)
        self.assertEqual("{abc}", value.json())

    def test_finding_group_by_name_success(self):
        self.mock_get.return_value = Mock(status_code=200)
        self.mock_get.return_value.json.return_value = json.loads(self.json_for_success)

        # test we can find bob, tim and nobody
        self.assertIsNotNone(self.fq.find_group_with_name("bob"))
        self.assertIsNotNone(self.fq.find_group_with_name("tim"))
        self.assertIsNotNone(self.fq.find_group_with_name("nobody"))
        self.assertIsNone(self.fq.find_group_with_name("jason"))

    def test_finding_group_by_name_fails_with_bad_response(self):
        self.mock_get.return_value = Mock(status_code=205)  # anything other than 200
        self.assertIsNone(self.fq.find_group_with_name("bob"))

    def test_ensure_inventory_query_group_exists_for_existing_group(self):
        self.mock_get.return_value = Mock(status_code=200)
        self.mock_get.return_value.json.return_value = json.loads(self.json_for_success)
        # ensure group "bob" exists, this should work
        (existing_group, was_created) = self.fq.ensure_inventory_query_group_exists("bob")
        self.assertIsNotNone(existing_group)
        self.assertFalse(was_created)

        url = None
        data = None

        def capture_the_post_vars(*args, **kwargs):
            nonlocal url, data
            url = args[0]
            data = kwargs["data"]

        # lets try one that does NOT exist
        with patch('extra_metrics.fwrest.requests.post') as post_mock:
            post_mock.side_effect = capture_the_post_vars
            (new_group, was_created) = self.fq.ensure_inventory_query_group_exists("sam")
            self.assertIsInstance(data, str)
            self.assertEqual('{"name": "sam"}', data)

    def test_get_all_inventory_queries_success(self):
        self.mock_get.return_value = Mock(status_code=200)
        self.mock_get.return_value.content = '{ "bannana": "awesome" }'
        result = self.fq.get_all_inventory_queries()
        self.assertTrue("bannana" in result)

    def test_get_all_inventory_queries_failure(self):
        self.mock_get.return_value = Mock(status_code=205) # anything other than 200
        result = self.fq.get_all_inventory_queries()
        self.assertIsNone(result)

    @patch('extra_metrics.fwrest.requests.post')
    def test_get_client_info_j_success_and_failure(self, post_mock):
        post_mock.return_value = Mock(status_code=200)
        post_mock.return_value.json.return_value = "this isn't actually json but wont matter"
        self.assertEqual("this isn't actually json but wont matter", self.fq.get_client_info_j())
        post_mock.return_value.status_code = 401
        self.assertRaises(Exception, self.fq.get_client_info_j)
        post_mock.return_value.status_code = 205
        self.assertIsNone(self.fq.get_client_info_j())

    def test_get_software_updates_web_ui_j_success_and_failure(self):
        self.mock_get.return_value = Mock(status_code=200)
        self.mock_get.return_value.json.return_value = {"bannana": "awesome"}
        result = self.fq.get_software_updates_web_ui_j()
        self.assertEqual("awesome", result["bannana"])

        self.mock_get.return_value.status_code = 401
        self.assertRaises(Exception, self.fq.get_software_updates_web_ui_j)
        self.mock_get.return_value.status_code = 205
        self.assertIsNone(self.fq.get_software_updates_web_ui_j())
