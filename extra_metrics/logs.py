
import logging
import sys
import os

logger = logging.getLogger('extra-metrics')


def init_logging():
    ch = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    # do we have a cmd line override for logging?
    logger.setLevel(os.getenv("EXTRA_METRICS_LOGLEVEL", "WARNING"))
