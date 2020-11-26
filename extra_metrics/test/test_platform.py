import unittest
import sys
from extra_metrics.platform import get_web_username


class TestPlatform(unittest.TestCase):
    def test_platform_web_username_is_right_on_win32(self):
        if sys.platform == 'darwin':
            self.assertEqual('_www', get_web_username())
        else:
            self.assertEqual('apache', get_web_username())
