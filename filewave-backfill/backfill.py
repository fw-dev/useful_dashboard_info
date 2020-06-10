import concurrent.futures
import re
from datetime import datetime, timezone, timedelta
from random import randint

import click
import progressbar
import requests


def process_metric(duration: float, freq: int, callback, show_progress=False):
    # Determine most historical timestamp; based on now - duration.
    # Step forward using freq interval. Generate random valued metric for given timestamp / metric name.
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=duration)
    bar = progressbar.ProgressBar(min_value=start_time.timestamp(), max_value=end_time.timestamp())
    while start_time < end_time:
        timestamp = start_time.timestamp() * 1e3
        callback(timestamp)
        start_time = start_time + timedelta(seconds=freq)
        bar.update(start_time.timestamp())


# TODO:
# - Labels on the metrics, and values for those labels (maybe multiple or random?)


@click.group()
def cli():
    click.echo("Yo!")


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

            process_metric(duration, freq, write_me_please, False)

    output_file.write("# EOF")

    output_file.close()
    metric_file.close()


class SkippedException(Exception):
    pass


def get_value_for_key(dict, key, description: str):
    if key not in dict:
        raise click.ClickException(f'Expected to see key {key} in {description} dictionary')
    return dict[key]


def expect_value_for_key(dict, key, expected_value, description: str, error='Response not valid'):
    value = get_value_for_key(dict, key, description)
    if value != expected_value:
        raise click.ClickException(f"Expected value for key {key} to equal '{expected_value}'. Got '{value}' instead")
    return value


def make_get_request_for_json(url):
    r = requests.get(url)
    if not r.ok:
        raise click.ClickException(f'Failed to talk to endpoint: {r.status_code}')
    return r.json()


def define_metric_for_this_url(metric_name: str, url, range: str):
    # click.echo(f"Finding labels for ... {metric_name}, range {range}")
    endpoint = f"{url}/api/v1/query?query={metric_name}[{range}]"
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

    # # We will get one result per label combination
    # def vector_handler():
    #     return {
    #         'metric_name': metric_name,
    #         'type': 'vector',
    #         'metric': data,
    #     }

    handlers = {
        # "vector": vector_handler,
        "matrix": matrix_handler,
    }
    if result_type not in handlers:
        raise click.ClickException(f"Dont know how to handle type {result_type} for key: {metric_name}")

    return handlers[result_type]()


@cli.command(name='create')
@click.option('-u', '--url', default="http://localhost:9090")
@click.option('-o', '--output', default="backfill_from_existing.txt")  # output file; will be overwritten
@click.option('-r', '--range', default="30m", help="How far to look back for values")
@click.option('-f', '--freq', default=15, help="frequency of samples", type=click.types.FLOAT)
@click.option('-d', '--duration', default=1, help="duration of data to create", type=click.types.FLOAT)
@click.option('-l', '--limit', help="If set, limit to the first N metrics. So dev doesn't take 100 years",
              type=click.types.INT)
@click.option('-t', '--threads', 'num_threads', default=100, help="How much damage to do", type=click.types.INT)
def create_from_existing(url, output, range: str, freq, duration, limit, num_threads):
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

    metrics_dict = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_metric_definitions = {executor.submit(define_metric_for_this_url, metric_name, url, range): metric_name
                                     for
                                     metric_name in all_the_metric_names}
        for future in concurrent.futures.as_completed(future_metric_definitions):
            metric_name = future_metric_definitions[future]
            try:
                metrics_dict[metric_name] = future.result()
            except SkippedException as se:
                click.echo(f"Warning: {se}")

    click.echo(f"Done. Defined {len(metrics_dict)} metrics from {url}")
    click.echo(f"Filling your SSD with text...")
    output_file = open(output, 'w')

    # Timestamps must be ascending, otherwise tsdb will crash with 'out of bounds'
    def write_all_metrics_for_this_ts(timestamp):
        valid_label_regex = r"[a-zA-Z_][a-zA-Z0-9_]*"

        for metric_name in list(metrics_dict.keys()):
            definition = metrics_dict[metric_name]
            results_array = definition["results"]

            # OK. So we have one or more results.
            # Lets spit out REAL values, over the time period required
            # We have one result per combination of labels. Each result has all the data for the range (from which we're going to pick one).
            for result_for_some_labels in results_array:
                labels_and_values = result_for_some_labels["metric"]
                valid_labels = {label: val for label, val in labels_and_values.items() if
                                label != "__name__" and re.match(valid_label_regex, label)}
                if len(valid_labels.keys()) < len(labels_and_values.keys()) - 1:
                    click.echo(f"Ignored some labels for {metric_name}")
                labels_with_vals = [f'{mn}="{val}"' for mn, val in valid_labels.items()]
                metric_label_part = "{" + ",".join(labels_with_vals) + "}"

                values_for_series = result_for_some_labels["values"]
                value_to_use = values_for_series[randint(0, len(values_for_series) - 1)]
                line = f"{metric_name}{metric_label_part} {value_to_use[1]} {timestamp}\n"
                output_file.write(line)

    process_metric(duration, freq, write_all_metrics_for_this_ts, True)

    # Don't have a \r\n, otherwise tsdb will crash with 'out of bounds'
    output_file.write("# EOF\n")
    output_file.close()


if __name__ == '__main__':
    cli(obj={})
