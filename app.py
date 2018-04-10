import logging
import argparse
import datetime

from flask import Flask
from config import LOGGER_CONFIG

app = Flask(__name__)
logger = logging.getLogger(LOGGER_CONFIG['NAME'])
FORMAT_STRING = '%I:%M:%S %p on %a, %b %d'
TIMEOUT = 5000
CSV_FILE_FORMAT = '{}-STATISTICS.csv'
VERSION = '1.0.0'
RELEASED = str(datetime.datetime(year=2017, month=4, day=5))
AUTHOR = 'Ava Thorn'
EMAIL = 'avthorn@cisco.com'

if __name__ == '__main__':
    from endpoints import *

    formatter = logging.Formatter(LOGGER_CONFIG['FORMAT'])

    fh = logging.FileHandler(LOGGER_CONFIG['FILENAME'])
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.setLevel(level=logging.DEBUG)
    logger.debug("Logger configured")

    parser = argparse.ArgumentParser()

    parser.add_argument('--reset', action='store_true')

    args = parser.parse_args()

    app.run(host='0.0.0.0', port=9998, debug=True)
