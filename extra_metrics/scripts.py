from extra_metrics.config import ExtraMetricsConfiguration, read_config_helper
from extra_metrics.fwrest import FWRestQuery
from extra_metrics.logs import logger, init_logging

import os
import click
import shutil
import pkg_resources
import sys


class ValidationExceptionCannotParseFileWaveVersion(Exception):
    pass


class ValidationExceptionWrongFileWaveVersion(Exception):
    pass


@click.group()
def cli():
    click.echo("FileWave Extra Metrics configuration.")


delay_30m = 60 * 30


@cli.command('validate', help="Validates the configuration assuming you are running this on the FileWave Server")
@click.option('-c', '--config-path', 'config_path', default=ExtraMetricsConfiguration.DEFAULT_CFG_FILE_LOCATION, help='the full path to the configuration file')
@click.option('-a', '--api-key', 'api_key', default=None, help='the FileWave API Key with appropriate rights to create groups/queries')
@click.option('-e', '--external-dns-name', 'external_dns_name', default=None, help='the externally visible DNS name for the filewave server')
@click.option('-i', '--interval', 'polling_interval', default=delay_30m, help='the seconds delay between successive queries against the FileWave system (default is 30m, 1800s)')
@click.option('-s', '--skip-local-validation', is_flag=True, default=False, help='skips the local server validation checks, useful when this isnt running on a fw server')
def install_into_environment(config_path, api_key, external_dns_name, polling_interval, skip_local_validation):
    init_logging()

    cfg = ExtraMetricsConfiguration()
    dirname = os.path.dirname(config_path)
    if not os.path.exists(dirname):
        logger.error(f"The directory for the configuration file does not exist: {dirname}")
        return

    if not os.path.exists(config_path) and os.path.isfile(config_path):
        if not os.access(config_path, os.W_OK):
            logger.error(f"The configuration file cannot be written to {config_path} - does this user have access?")
            return

    try:
        read_config_helper(cfg)
    except FileNotFoundError:
        if api_key is None or external_dns_name is None:
            logger.error("When there is no configuration file you must specify an API key and external DNS name, which will then be stored in the config file")
            return

    assert cfg.section is not None

    if api_key is not None:
        cfg.set_fw_api_key(api_key)
    if external_dns_name is not None:
        cfg.set_fw_api_server(external_dns_name)

    if polling_interval is not None:
        cfg.set_polling_delay_seconds(polling_interval)

    try:
        with open(config_path, 'w+') as f:
            cfg.write_configuration(f)
            logger.info(f"saved configuration to file: {config_path}")
    except Exception as e:
        logger.error("Unable to write the configuration file - normally this command requires sudo/root privs, did you use sudo?")
        logger.error(e)
        return

    if not skip_local_validation:
        try:
            provision_dashboards_into_grafana(cfg.get_fw_api_server())
            provision_prometheus_scrape_configuration()
            provision_supervisord_runtime()
        except Exception as e:
            logger.error("Error during provisioning of prometheus/grafana, are you using sudo?")
            logger.error(e)
            return

    q = FWRestQuery(cfg.get_fw_api_server(), cfg.get_fw_api_key())
    major, minor, patch = validate_runtime_requirements(q)

    log_config_summary(cfg, major, minor, patch)


def log_config_summary(cfg, major, minor, patch):
    logger.info("")
    logger.info("Extra Metrics - Configuration Summary")
    logger.info("=====================================")
    logger.info(f"External DNS     : {cfg.get_fw_api_server()}")
    logger.info(f"API Key          : {cfg.get_fw_api_key()}")
    logger.info(f"FileWave Server  : {major}.{minor}.{patch}")
    logger.info(f"Polling Interval : {cfg.get_polling_delay_seconds()} sec")


def provision_supervisord_runtime():
    supervisord_dir = os.path.join("/usr/local/etc/filewave/supervisor/", "extras")
    if not os.path.exists(supervisord_dir):
        os.makedirs(supervisord_dir)

    # lets go hunting, I want to find executable 'extra_metrics_run' - which is installed by setuptool,
    # but I don't know where the whole thing is being run from... so I'm looking for bin/extra_metrics_run
    # starting with the sys.executable directory
    exec_path = os.path.dirname(sys.executable)
    full_extra_metrics_run_path = "extra-metrics-run"
    for f in os.listdir(exec_path):
        if f == "extra-metrics-run":
            full_extra_metrics_run_path = os.path.join(exec_path, full_extra_metrics_run_path)

    data = pkg_resources.resource_string("extra_metrics.cfg", "extra_metrics_supervisord.conf").decode('utf-8')
    provisioning_file = os.path.join(supervisord_dir, 'extra_metrics_supervisord.conf')
    with open(provisioning_file, "w+") as f:
        new_data = data.replace(r'${EXTRA_METRICS_RUN}', full_extra_metrics_run_path)
        f.write(new_data)


def provision_dashboards_into_grafana(fw_server_dns_name):
    # if the expected dashboards DO NOT exist in the right path, moan about this and go ahead and copy them..
    grafana_dashboard_deployment_dir = os.path.join("/usr/local/etc/filewave/grafana/provisioning", "dashboards")
    if not os.path.exists(grafana_dashboard_deployment_dir):
        logger.error(f"The Grafana dashboard deployment directory ({grafana_dashboard_deployment_dir}) does not exist; is this version 14+ of FileWave?")
        return

    # check each file is there... overwrite regardless (helps on upgrade I suppose)
    for dashboard_file in pkg_resources.resource_listdir("extra_metrics", "dashboards"):
        if dashboard_file.endswith(".json"):
            data = pkg_resources.resource_string("extra_metrics.dashboards", dashboard_file).decode('utf-8')
            provisioning_file = os.path.join(grafana_dashboard_deployment_dir, dashboard_file)
            with open(provisioning_file, 'w+') as f:
                # load up the dashboard and replace the ${VAR_SERVER} with our config value of the external DNS
                new_data = data.replace('${VAR_SERVER}', fw_server_dns_name)
                f.write(new_data)
                logger.info(f"wrote dashboard file: {provisioning_file}")


def provision_prometheus_scrape_configuration():
    prometheus_dir = os.path.join("/usr/local/etc/filewave/prometheus/conf.d/jobs", "http")
    if not os.path.exists(prometheus_dir):
        logger.error(f"The Prometheus directory ({prometheus_dir}) does not exist; is this version 14+ of FileWave?")
        return

    for yaml_file in pkg_resources.resource_listdir("extra_metrics", "cfg"):
        if yaml_file.endswith(".yml"):
            data = pkg_resources.resource_string("extra_metrics.cfg", yaml_file)
            provisioning_file = os.path.join(prometheus_dir, yaml_file)
            with open(provisioning_file, 'wb') as f:
                f.write(data)
            shutil.chown(provisioning_file, user="apache", group="apache")


def validate_current_fw_version(fw_query):
    major, minor, patch = fw_query.get_current_fw_version_major_minor_patch()
    if major is None:
        raise ValidationExceptionCannotParseFileWaveVersion("Failed to detection which version of FileWave is running")

    if major < 14:
        err = f"You must be running FileWave version 14 or above - I detected a FileWave server version: {major}.{minor}.{patch}"
        logger.error(err)
        raise ValidationExceptionWrongFileWaveVersion(err)

    return major, minor, patch


def validate_current_api_keys_rights(fw_query):
    pass


def validate_runtime_requirements(q):
    # TODO: can I upgrade the grafana pie chart automatically?
    validate_current_api_keys_rights(q)
    return validate_current_fw_version(q)

