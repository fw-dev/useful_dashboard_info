import unittest
from extra_metrics.fwrest import FWRestQuery
from extra_metrics.config import read_config_helper, ExtraMetricsConfiguration


class FWQueryTestCase(unittest.TestCase):
    def test_query_init(self):
        fq = FWRestQuery("a", "b")
        self.assertEqual(fq.hostname, "a")
        self.assertEqual(fq.api_key, "b")

    def test_query_inventory_stub(self):
        fq = FWRestQuery("a", "b")
        self.assertEqual("https://a:20445/inv/api/v1/def",
                         fq._fw_run_inv_query("def"))
        self.assertEqual("https://a/api/xyz", fq._fw_run_web_query("xyz"))

    # @unittest.skip()
    # def test_live_get_software_patches_j(self):
    #     cfg = ExtraMetricsConfiguration()
    #     read_config_helper(cfg)
    #     fw_q = FWRestQuery(cfg.get_fw_api_server(), cfg.get_fw_api_key())
    #     r = fw_q.get_software_patches_j()
    #     assert r is not None
