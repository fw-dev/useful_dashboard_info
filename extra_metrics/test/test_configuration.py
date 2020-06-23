import io
import unittest
import unittest.mock as mock

from extra_metrics.logs import logger
from extra_metrics.config import ExtraMetricsConfiguration
from extra_metrics.test.fake_mocks import FakeQueryInterface

from extra_metrics.scripts import (
    running_on_a_fwxserver_host,
    validate_current_fw_version, ValidationExceptionCannotParseFileWaveVersion,
    ValidationExceptionWrongFileWaveVersion
)


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.cfg = ExtraMetricsConfiguration()
        self.config_text = '''
            [extra_metrics]
            fw_server_hostname = abc
            fw_server_api_key = def
            '''
        buf = io.StringIO(self.config_text)
        self.cfg.read_configuration(buf)

    def test_configuration_defaults(self):
        self.assertEqual("abc", self.cfg.get_fw_api_server())
        self.assertEqual("def", self.cfg.get_fw_api_key())
        self.assertEqual(True, self.cfg.get_verify_tls())

    def test_configuration_changes_are_written(self):
        self.cfg.set_fw_api_key('hello world')
        self.cfg.set_polling_delay_seconds(42)
        buf = io.StringIO()
        self.cfg.write_configuration(buf)
        value = buf.getvalue()
        self.assertTrue("hello world" in value)
        self.assertTrue("42" in value)
        self.assertEqual(self.cfg.get_polling_delay_seconds(), 42)

        self.assertEqual(True, self.cfg.get_verify_tls())
        self.cfg.set_verify_tls(False)
        self.assertEqual(False, self.cfg.get_verify_tls())

        self.cfg.set_verify_tls(True)
        self.assertEqual(True, self.cfg.get_verify_tls())


def get_unparsable_version(self):
    return None, None, None


def get_incorrect_version(self):
    return 13, 3, 0


def get_correct_version(self):
    return 14, 0, 0


class TestRuntimeChecks(unittest.TestCase):
    def setUp(self):
        self.fw_query = FakeQueryInterface()

    @mock.patch('extra_metrics.test.fake_mocks.FakeQueryInterface.get_current_fw_version_major_minor_patch', get_unparsable_version)
    def test_validation_fails_due_to_bad_parsing(self):
        with self.assertRaises(ValidationExceptionCannotParseFileWaveVersion):
            validate_current_fw_version(self.fw_query)

    @mock.patch('extra_metrics.test.fake_mocks.FakeQueryInterface.get_current_fw_version_major_minor_patch', get_correct_version)
    def test_validation_succeeds(self):
        validate_current_fw_version(self.fw_query)

    @mock.patch('extra_metrics.test.fake_mocks.FakeQueryInterface.get_current_fw_version_major_minor_patch', get_incorrect_version)
    def test_validation_finds_incorrect_version(self):
        with self.assertRaises(ValidationExceptionWrongFileWaveVersion):
            validate_current_fw_version(self.fw_query)

    def test_running_on_fwxserver_host(self):
        def my_check(yes_or_no, file_path):
            logger.info("checking file path:", file_path)
            return yes_or_no

        self.assertTrue(running_on_a_fwxserver_host(exist_func=lambda f: my_check(True, f)))
        self.assertFalse(running_on_a_fwxserver_host(exist_func=lambda f: my_check(False, f)))