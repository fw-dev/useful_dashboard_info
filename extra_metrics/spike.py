#!/usr/local/bin/python

from prometheus_client import REGISTRY
from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client import start_http_server
import time


class SampleAppCollector(object):
    app_version = None
    app_name = None
    count = None

    def __init__(self, name, version, count):
        self.app_name = name
        self.app_version = version
        self.count = count

    def collect(self):
        gauge = GaugeMetricFamily("extra_metrics_application_count",
                                  'Counts the number of app/version combinations',
                                  labels=['name', 'version'])
        gauge.add_metric([self.app_name, self.app_version], self.count)
        yield gauge


class KingOfThings(object):
    def __init__(self):
        self.counter = 0
        self.collector = None
        # self.registry = CollectorRegistry(auto_describe=True)
        self.registry = REGISTRY
        self.iterateCollector()

    def iterateCollector(self):
        self.counter += 1
        if self.collector is not None:
            self.registry.unregister(self.collector)
        self.collector = SampleAppCollector("photoshop", str(self.counter), self.counter)
        self.registry.register(self.collector)


if __name__ == "__main__":
    start_http_server(8000)
    k = KingOfThings()
    while(True):
        time.sleep(1)
        k.iterateCollector()
