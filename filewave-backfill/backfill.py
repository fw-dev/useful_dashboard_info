import concurrent.futures
import os
import re, sys, shutil
import subprocess
from datetime import datetime, timezone, timedelta
from random import randint

import click
import progressbar
import requests

def process_metric(duration: float, freq: int, callback):
    # Determine most historical timestamp; based on now - duration.
    # Step forward using freq interval. Generate random valued metric for given timestamp / metric name.
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=duration)
    while start_time < end_time:
        timestamp = start_time.timestamp() * 1e3
        callback(timestamp)
        start_time = start_time + timedelta(seconds=freq)


@click.group()
def cli():
    click.echo("Importer of impending doom. Welcome. Please take a seat.")


"""
This was my original idea.
Create metrics based off some specification file; and then feed that file into tsdb.
Problem is the values are meaningless and there are no labels.

This method should probably be deleted.
Only left here in case the other one (create) turns out to be bad for some reason.
"""


@cli.command(name='makedata')
@click.option('-m', '--metrics', default="fw_metrics.txt")
@click.option('-o', '--output', default="backfill_dump.txt")  # output file; will be overwritten
@click.option('-f', '--freq', default=15, help="frequency of samples", type=click.types.FLOAT)
@click.option('-d', '--duration', default=1, help="duration of data to create", type=click.types.FLOAT)
def backfill_importer(metrics, output, freq, duration):
    metric_regex = r"(.+?) (\d+) (\d+)$"
    click.echo(f"Using metric specification: {metrics}")
    metric_file = open(metrics, "r")
    output_file = open(output, 'w')

    last_metric_name = None
    for line in progressbar.progressbar(metric_file):
        line = line.strip()
        match = re.search(metric_regex, line)
        if match:
            metric_name = match.group(1)
            metric_min = int(match.group(2))
            metric_max = int(match.group(3))
            if last_metric_name != metric_name:
                print(f"Processing: {metric_name}, {metric_min}/{metric_max}")

            def write_me_please(timestamp):
                metric_value = randint(metric_min, metric_max)
                metric_line = f"{metric_name} {metric_value} {int(timestamp)}"
                output_file.write(metric_line)

            process_metric(duration, freq, write_me_please)

    output_file.write("# EOF")

    output_file.close()
    metric_file.close()


class SkippedException(Exception):
    pass


def get_value_for_key(some_dict, key, description: str):
    if key not in some_dict:
        raise click.ClickException(f'Expected to see key {key} in {description} dictionary')
    return some_dict[key]


def expect_value_for_key(some_dict, key, expected_value, description: str):
    value = get_value_for_key(some_dict, key, description)
    if value != expected_value:
        raise click.ClickException(f"Expected value for key {key} to equal '{expected_value}'. Got '{value}' instead")
    return value


def make_get_request_for_json(url):
    r = requests.get(url)
    if not r.ok:
        raise click.ClickException(f'Failed to talk to endpoint: {r.status_code}')
    return r.json()


def define_metric_for_this_url(metric_name: str, url, prom_date_range: str):
    # click.echo(f"Finding labels for ... {metric_name}, range {range}")
    endpoint = f"{url}/api/v1/query?query={metric_name}[{prom_date_range}]"
    json = make_get_request_for_json(endpoint)

    expect_value_for_key(json, "status", "success", f"response for label query for : {metric_name}")
    data = get_value_for_key(json, "data", f"data for the response for: {metric_name}")
    result_type = get_value_for_key(data, "resultType", f"type of result returned for {metric_name}")
    results_array = get_value_for_key(data, "result", f"result of label query for {metric_name}")

    if len(results_array) < 1:
        raise SkippedException(f"got no query result, for: {metric_name}. Skipped.")

    # Getting a range of values.
    # This gets us both various series relating to the metric; and values for the range
    def matrix_handler():
        return {
            'metric_name': metric_name,
            'type': "matrix",
            'results': results_array,
        }

    handlers = {
        "matrix": matrix_handler,
    }
    if result_type not in handlers:
        raise click.ClickException(f"Dont know how to handle type {result_type} for key: {metric_name}")

    return handlers[result_type]()


@cli.command(name='create')
@click.option('-u', '--url', default="http://localhost:9090")
@click.option('-m', '--metric', 'metrics', multiple=True, default=[], help="A metric name, eg: filewave_server_license_status. Can be specified multiple times")
@click.option('-o', '--output', 'output_path', default="backfill_data", help='name of folder to use for created data')
@click.option('-r', '--range', 'prom_date_range', default="30m", help="How far to look back for values")
@click.option('-f', '--freq', default=15, help="frequency of samples", type=click.types.FLOAT)
@click.option('-d', '--duration', default=1, help="duration of data to create, in days", type=click.types.FLOAT)
@click.option('-p', '--target-platform', 'target_platform', show_default=True, default=sys.platform, help='target platform where the TSDB import takes place, e.g. what server is prometheus running on (darwin/linux)', type=click.types.STRING)
@click.option('-l', '--limit', help="If set, limit to the first N metrics. So dev doesn't take 100 years. Only active if -m not specified.",
              type=click.types.INT)
@click.option('-t', '--threads', 'num_threads', default=100, help="How much damage to do all at once", type=click.types.INT)
def create_from_existing(url, metrics, output_path, prom_date_range: str, freq, duration, target_platform, limit, num_threads):
    if len(metrics) == 0:
        endpoint = f"{url}/api/v1/label/__name__/values"
        click.echo(f"Reading from {endpoint}")
        r = requests.get(endpoint)
        if not r.ok:
            raise click.ClickException(f'Failed to talk to endpoint: {r.status_code}')
        json_payload = r.json()

        # Expect 'status' == success
        expect_value_for_key(json_payload, "status", "success", "main response")

        # Should use regex for this, and add as @click.option
        all_the_metric_names = [n for n in json_payload["data"] if
                                n not in ['ALERTS', 'ALERTS_FOR_STATE', 'up', 'redis_up']]

        # Do the top 10
        if limit:
            all_the_metric_names = all_the_metric_names[:limit]
    else:
        all_the_metric_names = metrics

    metrics_dict = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_metric_definitions = {
            executor.submit(define_metric_for_this_url, metric_name, url, prom_date_range): metric_name
            for metric_name in all_the_metric_names
        }
        for future in concurrent.futures.as_completed(future_metric_definitions):
            metric_name = future_metric_definitions[future]
            try:
                metrics_dict[metric_name] = future.result()
            except SkippedException as se:
                click.echo(f"Warning: {se}")

    click.echo(f"Done. Defined {len(metrics_dict)} metrics from {url}")
    click.echo(f"Filling your SSD with text...")

    valid_label_regex = r"[a-zA-Z_][a-zA-Z0-9_]*"

    if not os.path.exists(output_path):
        click.echo(f"Making output folder: {output_path}")
        os.makedirs(output_path)

    # Copy the right TSDB thing to the output folder...
    shutil.copy(f"./tsdb-{target_platform}", os.path.join(output_path, f"tsdb"))

    # Timestamps must be ascending, otherwise tsdb will crash with 'out of bounds'
    def write_single_file_for_metric(metric_name):
        output_file_name = os.path.join(output_path, f"{metric_name}.txt")
        output_file = open(output_file_name, 'w')

        def write_all_metrics_for_this_ts(timestamp):
            definition = metrics_dict[metric_name]
            results_array = definition["results"]

            def fix_label_values(value):
                return value.replace("\n", " ")

            # OK. So we have one or more results. Lets spit out REAL values, over the time period required We have
            # one result per combination of labels. Each result has all the data for the range (from which we're
            # going to pick one).
            for result_for_some_labels in results_array:
                labels_and_values = result_for_some_labels["metric"]
                valid_labels = {label: fix_label_values(val) for label, val in labels_and_values.items() if
                                label != "__name__" and re.match(valid_label_regex, label)}
                if len(valid_labels.keys()) < len(labels_and_values.keys()) - 1:
                    click.echo(f"Ignored some labels for {metric_name}")
                labels_with_vals = [f'{mn}="{val}"' for mn, val in valid_labels.items()]
                metric_label_part = "{" + ",".join(labels_with_vals) + "}"

                values_for_series = result_for_some_labels["values"]
                value_to_use = values_for_series[randint(0, len(values_for_series) - 1)]
                line = f"{metric_name}{metric_label_part} {value_to_use[1]} {timestamp}\n"
                output_file.write(line)

        process_metric(duration, freq, write_all_metrics_for_this_ts)

        # Don't have a \r\n, otherwise tsdb will crash with 'out of bounds'
        output_file.write("# EOF\n")
        output_file.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as file_executor:
        future_files = {file_executor.submit(write_single_file_for_metric, mn): mn for mn in metrics_dict.keys()}
        for future in concurrent.futures.as_completed(future_files):
            future.result()

    # for metric_name in list(metrics_dict.keys()):


@cli.command('import', help="Imports all the files (using tsdb import) created by the 'create' command")
@click.option('-i', '--input', 'input_path', default="backfill_data", help='name of folder to use for created data')
@click.option('-d', '--data', 'data_path', default="data", help='location of prometheus tsdb')
@click.option('-c', '--done', 'done_path', default="backfill_done", help='where to move files when successfully imported')
def import_from_folder(input_path, data_path, done_path):
    if not os.path.exists(done_path):
        os.mkdir(done_path)

    """
    find backfill_data/ -type f -exec tsdb-linux import {} data/ \;
    """

    TSDB_EXE_NAME = f"./tsdb"

    for file in os.listdir(input_path):
        file_name = os.path.join(input_path, file)
        command = [TSDB_EXE_NAME, "import", file_name, data_path]
        click.echo(f"Processing: {file}")
        tsdb_run = subprocess.run(command)
        if tsdb_run.returncode != 0:
            raise click.ClickException(f"Failed to run with file: {file}, error: {tsdb_run.returncode}")
        print(f"{file} OK. Result: {tsdb_run.returncode}.")
        os.rename(file_name, os.path.join(done_path, file))


if __name__ == '__main__':
    cli(obj={})
