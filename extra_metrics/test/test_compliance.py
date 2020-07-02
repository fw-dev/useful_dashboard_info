import unittest
from extra_metrics.compliance import ClientCompliance


class TestClientComplianceCase(unittest.TestCase):
    def test_compliance_for_div_by_zero(self):
        c = ClientCompliance(0, 0, 0)
        self.assertEqual(c.get_disk_compliance(), ClientCompliance.STATE_UNKNOWN)

    def test_compliance_with_no_data(self):
        c = ClientCompliance(None, None, None)
        self.assertEqual(c.get_checkin_compliance(),
                         ClientCompliance.STATE_UNKNOWN)
        self.assertEqual(c.get_disk_compliance(),
                         ClientCompliance.STATE_UNKNOWN)
        self.assertEqual(c.get_compliance_state(),
                         ClientCompliance.STATE_UNKNOWN)
        self.assertEqual(c.get_patch_compliance(),
                         ClientCompliance.STATE_UNKNOWN)

    def test_compliance_patch_status_ok(self):
        c = ClientCompliance(None, None, None, 0, 0)
        self.assertEqual(c.get_patch_compliance(),
                         ClientCompliance.STATE_OK)

    def test_compliance_patch_status_failure(self):
        # 1 critical package, no other packages
        c = ClientCompliance(None, None, None, 1, 0)
        self.assertEqual(c.get_patch_compliance(),
                         ClientCompliance.STATE_ERROR)
        # 0 critical packages, 1 other package
        c = ClientCompliance(None, None, None, 0, 1)
        self.assertEqual(c.get_patch_compliance(),
                         ClientCompliance.STATE_WARNING)

    def test_compliance_checkin_less_than_7_is_ok(self):
        c = ClientCompliance(None, None, 6)
        self.assertEqual(c.get_checkin_compliance(), ClientCompliance.STATE_OK)
        c.last_checkin_days = 7
        self.assertEqual(c.get_checkin_compliance(),
                         ClientCompliance.STATE_WARNING)

    def test_compliance_checkin_less_than_14_is_warning(self):
        c = ClientCompliance(None, None, 13)
        self.assertEqual(c.get_checkin_compliance(),
                         ClientCompliance.STATE_WARNING)
        c.last_checkin_days = 14
        self.assertEqual(c.get_checkin_compliance(),
                         ClientCompliance.STATE_ERROR)

    def test_compliance_disk_space_free_more_than_20pcnt(self):
        # < 20% left is warning
        # < 5% left is critical, or less than 5g
        c = ClientCompliance(100, 25, 3)
        self.assertEqual(c.get_disk_compliance(), ClientCompliance.STATE_OK)
        c = ClientCompliance(100, 20, 3)
        self.assertEqual(c.get_disk_compliance(), ClientCompliance.STATE_OK)

    def test_compliance_disk_space_free_between_5_and_20pcnt(self):
        c = ClientCompliance(100, 5, 3)
        self.assertEqual(c.get_disk_compliance(),
                         ClientCompliance.STATE_WARNING)
        c = ClientCompliance(100, 19, 3)
        self.assertEqual(c.get_disk_compliance(),
                         ClientCompliance.STATE_WARNING)

    def test_compliance_disk_space_free_less_than_5pcnt(self):
        c = ClientCompliance(100, 4.9, 3)
        self.assertEqual(c.get_disk_compliance(), ClientCompliance.STATE_ERROR)

    def test_compliance_value_is_max_of_either(self):
        # enforce that it's max() of either value
        c1 = ClientCompliance(100, 5, 3)  # WARNING for DISK
        c2 = ClientCompliance(100, 40, 500)  # ERROR for CHECKIN DAYS
        self.assertTrue(c2.get_checkin_compliance() > c1.get_disk_compliance())
        self.assertEqual(c2.get_compliance_state(),
                         ClientCompliance.STATE_ERROR)
