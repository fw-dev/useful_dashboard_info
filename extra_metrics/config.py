import configparser
import os 
from extra_metrics.logs import logger

def read_config_helper(cfg):
    try:
        logger.info(f"loading the configuration from file {ExtraMetricsConfiguration.DEFAULT_CFG_FILE_LOCATION}")
        with open(ExtraMetricsConfiguration.DEFAULT_CFG_FILE_LOCATION, 'r') as f:
            cfg.read_configuration(f)
            return True
    except Exception:
        logger.info(f"trying the .extra_metrics.ini file in {os.getcwd()}")
        with open(os.path.join(os.getcwd(), ".extra_metrics.ini"), 'r') as f:
            cfg.read_configuration(f)
            return True
    return False

class ExtraMetricsConfiguration:
    DEFAULT_CFG_FILE_LOCATION = '/usr/local/etc/filewave/extra_metrics.ini'
    KEY_FW_SERVER_HOSTNAME = 'fw_server_hostname'
    KEY_FW_SERVER_API_KEY = 'fw_server_api_key'
    KEY_POLLING_DELAY = 'fw_query_polling_delay_seconds'

    def __init__(self):
        self.config = configparser.ConfigParser()
                
    def read_configuration(self, file_obj):
        self.config.read_file(file_obj)
        self.section = self.config['extra_metrics']

    def write_configuration(self, file_obj):
        self.config.write(file_obj)
    
    def _get_value(self, attr_name, default=None):
        return self.section.get(attr_name, default)

    def _set_value(self, attr_name, value):
        self.section[attr_name] = value

    def get_fw_api_server(self):
        return self._get_value(ExtraMetricsConfiguration.KEY_FW_SERVER_HOSTNAME)
    def set_fw_api_server(self, value):
        self._set_value(ExtraMetricsConfiguration.KEY_FW_SERVER_HOSTNAME, value)

    def get_fw_api_key(self):    
        return self._get_value(ExtraMetricsConfiguration.KEY_FW_SERVER_API_KEY)
    def set_fw_api_key(self, value):
        self._set_value(ExtraMetricsConfiguration.KEY_FW_SERVER_API_KEY, value)

    def get_polling_delay_seconds(self):    
        # default is 5 mins
        return self._get_value(ExtraMetricsConfiguration.KEY_POLLING_DELAY, 30)
    def set_polling_delay_seconds(self, value):
        self._set_value(ExtraMetricsConfiguration.KEY_POLLING_DELAY, value)
