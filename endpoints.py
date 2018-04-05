import flask
import traceback
import pprint

from app import app, logger
from cronbot import CronBot
from queuebot import Bot
from ciscosparkapi import CiscoSparkAPI
from config import QUEUE_BOT

@app.route('/cronbot', methods=['GET'])
def cron():
    bot = CronBot()

@app.route('/queuebot', methods=['POST'])
def queue():
    try:
        data = flask.request.json
        if data:
            logger.debug(pprint.pformat(data))

            logger.debug('Initializing Spark API')
            api = CiscoSparkAPI(QUEUE_BOT)
            logger.debug('Spark API initialized')

            data = data['data']

            if data.get('mentionedPeople') and api.people.me().id in data['mentionedPeople']:
                Bot(api, data).handle_data(data)

            return ''

        else:
            return 'NO STOP PLEASE STOP'
    except Exception as e:
        raise
        print(traceback.format_exc())
        logger.error(traceback.format_exc())
        return '500 Internal Server Error'