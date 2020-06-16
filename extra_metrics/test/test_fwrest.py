import unittest
from extra_metrics.fwrest import FWRestQuery


class ExtraMetricsQueryTestCase(unittest.TestCase):
    def test_query_init(self):
        fq = FWRestQuery("a", "b")
        self.assertEqual(fq.hostname, "a")
        self.assertEqual(fq.api_key, "b")

    def test_query_inventory_stub(self):
        fq = FWRestQuery("a", "b")
        self.assertEqual("https://a:20445/inv/api/v1/def",
                         fq._fw_run_inv_query("def"))
        self.assertEqual("https://a/api/xyz", fq._fw_run_web_query("xyz"))
