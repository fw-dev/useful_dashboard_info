from prometheus_client import start_http_server
from extra_metrics.logs import logger, init_logging
from extra_metrics.scripts import log_config_summary
from periodic import Periodic
import pandas as pd
import asyncio
import json

from extra_metrics.application import ApplicationQueryManager
from extra_metrics.softwarepatches import SoftwarePatchStatus
from extra_metrics.devices import PerDeviceStatus
from extra_metrics.fwrest import FWRestQuery
from extra_metrics.fw_zmq_eventsub import ZMQConnector
from extra_metrics.config import ExtraMetricsConfiguration, read_config_helper

# TODO: to make associations clickable, direct users into the extra-metrics program, have that inject a real FW query on the fly and then redirect to that.

# TODO: mock the fwrestquery API itself, to prove that all methods produce the right reactions.

# TODO: DEVICE HEALTH show the reasons/state of health of a device in (my app or) custom fields so it can be reported on

# TODO: DEVICE HEALTH - if a query underneath a special group is called 'Extra Health Checks'; then clients have to be part of that to be healthy.  Question; if they are not - what error message is produced?

# TODO: consider alerts for devices entering a non-healthy state for the first time today

# TODO: consider how I might achieve a cannibalization test for devices?

# TODO: write documentation on arch and reasoning... perhaps using the Wiki in GitHub

# TODO: languages / translation?

pd.set_option('display.precision', 3)
pd.set_option('display.expand_frame_repr', False)


class MainRuntime:
    def __init__(self, logger):
        self.cfg = None
        self.zmq_sub = None
        self.app_qm = None
        self.software_patches = None
        self.per_device = None
        self.logger = logger
        self.rerun_data_collection = True

    def init_services(self):
        self.cfg = ExtraMetricsConfiguration()
        read_config_helper(self.cfg)

        self.fw_query = FWRestQuery(
            hostname=self.cfg.get_fw_api_server_hostname(),
            api_key=self.cfg.get_fw_api_key(),
            verify_tls=self.cfg.get_verify_tls())

        self.app_qm = ApplicationQueryManager(self.fw_query)
        self.software_patches = SoftwarePatchStatus(self.fw_query)
        self.per_device = PerDeviceStatus(self.fw_query)

        self.zmq_sub = ZMQConnector(self.cfg, lambda topic, payload: self.event_callback(topic, payload))

    def event_callback(self, topic, payload):
        self.logger.info(f"event received: {topic}")

        interesting_topics = [
            "/server/update_model_finished",
            "/api/auditlog",
        ]

        debug_topics = interesting_topics + [
            "/inventory/inventory_query_changed",
            "/server/change_packets",
            "/client/"
        ]

        for test_topic in debug_topics:
            if topic.startswith(test_topic):
                pretty_print_json = json.dumps(payload, indent=4)
                logger.info(f"topic: {topic}")
                logger.info(f"payload: {pretty_print_json}")

        if topic in interesting_topics:
            if topic == "/api/auditlog" and "Report Created" not in payload["message"]:
                return

            # set a flag in state indicating that the data collection should run imminently
            logger.info(f"topic {topic} fired; will re-queue data collection")
            self.rerun_data_collection = True

    async def validate_and_collect_data(self):
        self.app_qm.validate_query_definitions()
        self.app_qm.collect_application_query_results()

        self.software_patches.collect_patch_data_status()
        # WARNING; the per_device class relies on data collected from software updates, keep
        # this order of execution.
        self.per_device.collect_client_data(self.software_patches)

        self.rerun_data_collection = False


async def create_program_and_run_it():
    init_logging()

    prog = MainRuntime(logger)
    prog.init_services()
    start_http_server(8000)

    host = prog.cfg.get_fw_api_server_hostname()
    poll_interval = prog.cfg.get_polling_delay_seconds()
    logger.info(f"Extra Metrics - connecting to {host}, using poll interval of {poll_interval} sec")

    # fetches and stores the current server version, this is important as the REST API's depend on this
    # information.  Prior to 14.2.0 some of the API calls were different and 14.2.0 put them all under ../api/v1/...
    prog.fw_query.fetch_server_version()

    log_config_summary(prog.cfg, prog.fw_query.major_version, prog.fw_query.minor_version, prog.fw_query.patch_version)

    if prog.fw_query.major_version is None or prog.fw_query.major_version == 0:
        logger.error("Unable to reach FileWave server, aborting...")
        return

    p = Periodic(poll_interval, prog.validate_and_collect_data)
    await p.start()

    while(True):
        if prog.rerun_data_collection:
            await prog.validate_and_collect_data()
        await asyncio.sleep(1)


def serve_and_process():
    asyncio.run(create_program_and_run_it())


async def create_program_and_run_tests():
    init_logging()
    prog = MainRuntime(logger)
    prog.init_services()
    prog.software_patches.collect_patch_data_status()
    prog.per_device.collect_client_data(prog.software_patches)


def run_tests():
    asyncio.run(create_program_and_run_tests())


if __name__ == "__main__":
    serve_and_process()
