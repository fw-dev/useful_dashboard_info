import io
import sys
import unittest
import unittest.mock as mock

from extra_metrics.config import ExtraMetricsConfiguration

from extra_metrics.scripts import provision_supervisord_runtime, \
        validate_current_fw_version, ValidationExceptionCannotParseFileWaveVersion, \
        ValidationExceptionWrongFileWaveVersion


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

    def test_configuration_changes_are_written(self):
        self.cfg.set_fw_api_key('hello world')
        self.cfg.set_polling_delay_seconds(42)
        buf = io.StringIO()
        self.cfg.write_configuration(buf)
        value = buf.getvalue()
        self.assertTrue("hello world" in value)
        self.assertTrue("42" in value)
        self.assertEqual(self.cfg.get_polling_delay_seconds(), "42")


def get_unparsable_version():
    return "13.3.3"


def get_incorrect_version():
    return "fwxserver 13.3.3"


def get_correct_version():
    return "fwxserver 14.0.0"


class TestRuntimeChecks(unittest.TestCase):
    @mock.patch('extra_metrics.scripts.get_current_fw_version', get_unparsable_version)
    def test_validation_fails_due_to_bad_parsing(self):
        with self.assertRaises(ValidationExceptionCannotParseFileWaveVersion):
            validate_current_fw_version()

    @mock.patch('extra_metrics.scripts.get_current_fw_version', get_correct_version)
    def test_validation_succeeds(self):
        validate_current_fw_version()

    @mock.patch('extra_metrics.scripts.get_current_fw_version', get_incorrect_version)
    def test_validation_finds_incorrect_version(self):
        with self.assertRaises(ValidationExceptionWrongFileWaveVersion):
            validate_current_fw_version()

    def test_can_run_supervisord_provisioning(self):
        provision_supervisord_runtime()

