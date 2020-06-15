from extra_metrics.main import serve_and_process
from extra_metrics.config import ExtraMetricsConfiguration, read_config_helper
from extra_metrics.logs import logger, init_logging

import json
import os
import click
import shutil
import pkg_resources

@click.group()
def cli():
    click.echo("FileWave Extra Metrics configuration.")


@cli.command('validate', help="Validates the configuration assuming you are running this on the FileWave Server")
@click.option('-c', '--config-path', 'config_path', default=ExtraMetricsConfiguration.DEFAULT_CFG_FILE_LOCATION, help='the full path to the configuration file')
@click.option('-a', '--api-key', 'api_key', default=None, help='the FileWave API Key with appropriate rights to create groups/queries')
@click.option('-e', '--external-dns-name', 'external_dns_name', default=None, help='the externally visible DNS name for the filewave server')
@click.option('-v', '--validate', 'validate', default=True, help='if config is present, validate some basic requirements by calling the FW server using the API Key')
def install_into_environment(config_path, api_key, external_dns_name, validate):
    cfg = ExtraMetricsConfiguration()
    
    # TODO: get the API key from the bearer_token_file - abort if not there.  assumes we are running localhost

    dirname = os.path.dirname(config_path)
    if not os.path.exists(dirname):
        logger.error(f"The directory for the configuration file does not exist: {dirname}")
        return

    if not os.path.exists(config_path) and os.path.isfile(config_path):
        if not os.access(config_path, os.W_OK):
            logger.error(f"The configuration file cannot be written to {config_path} - does this user have access?")
            return

    read_config_helper(cfg)

    if api_key is not None:
        cfg.set_fw_api_key(api_key)
    if external_dns_name is not None:
        cfg.set_fw_api_server(external_dns_name)

    with open(config_path, 'w+') as f:
        cfg.write_configuration(f)
        logger.info(f"saved configuration to file: {config_path}")

    provision_dashboards_into_grafana(cfg.get_fw_api_server())
    provision_prometheus_scrape_configuration()

    logger.info("")
    logger.info("Configuration Summary")
    logger.info("=====================")
    logger.info(f"API Key: {cfg.get_fw_api_key()}")
    logger.info(f"External DNS: {cfg.get_fw_api_server()}")

    validate_runtime_requirements(cfg)


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


def validate_runtime_requirements(cfg):
    # TODO: does the API key have the appropriate rights? 
    # TODO: can I upgrade the grafana pie chart automatically? 
    pass
