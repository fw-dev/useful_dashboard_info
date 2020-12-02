import unittest
from extra_metrics.fwrest import FWRestQuery
# from extra_metrics.config import read_config_helper


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
