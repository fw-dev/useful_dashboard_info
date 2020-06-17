import unittest
from extra_metrics.test.fake_mocks import FakeQueryInterface
from extra_metrics.softwarepatches import SoftwarePatchStatus


class TestSoftwarePatchFetching(unittest.TestCase):
    def setUp(self):
        self.fw_query = FakeQueryInterface()

    def test_that_zero_data_doesnt_cause_bad_things(self):
        mgr = SoftwarePatchStatus(self.fw_query)
        mgr.collect_patch_data_status()
