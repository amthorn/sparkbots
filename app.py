import logging
import argparse
import datetime

from flask import Flask
from config import LOGGER_CONFIG

app = Flask(__name__)
logger = logging.getLogger(LOGGER_CONFIG['NAME'])
FORMAT_STRING = '%I:%M:%S %p on %a, %b %d'
TIMEOUT = 5000
CSV_FILE_FORMAT = '{}-{}-STATISTICS.csv'
VERSION = '1.1.0'
RELEASED = str(datetime.datetime(year=2017, month=4, day=11))
AUTHOR = 'Ava Thorn'
EMAIL = 'avthorn@cisco.com'
QUEUE_THRESHOLD = 50
MAX_FLUSH_THRESHOLD = 3122064000  # 99 years in seconds
PROJECT_STALE_SECONDS_FIRST = 7 * (24 * 60 * 60)  # How many days before first warning of stale project
PROJECT_STALE_SECONDS_SECOND = 14 * (24 * 60 * 60)  # How many days before second warning of stale project
PROJECT_STALE_SECONDS_FINAL = 20 * (24 * 60 * 60)  # How many days before final warning of stale project
PROJECT_STALE_SECONDS = 21 * (24 * 60 * 60)  # How many days before project becomes stale
RELEASE_NOTES = 'release_notes.json'
RANDOM_EASTER_REJECTION = 0.05
DEFAULT_SUBPROJECT = 'GENERAL'

if __name__ == '__main__':
    from endpoints import *

    formatter = logging.Formatter(LOGGER_CONFIG['FORMAT'])

    fh = logging.FileHandler(LOGGER_CONFIG['FILENAME'])
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.setLevel(level=logging.DEBUG)
    logger.debug("Logger configured")

    import scheduler

    app.run(host='0.0.0.0', port=9998, debug=True)
