import flask
import traceback
import pprint

from app import app, logger
from cronbot import CronBot
from queuebot import Bot
from ciscosparkapi import CiscoSparkAPI
from config import QUEUE_BOT, PRODUCTION

BOT = None

@app.route('/cronbot', methods=['GET'])
def cron():
    bot = CronBot()

@app.route('/queuebot', methods=['POST'])
def queue():
    try:
        data = flask.request.json
        if data:

            logger.debug('Initializing Spark API')
            if PRODUCTION:
                api = CiscoSparkAPI(QUEUE_BOT)
            else:
                from config import DEV_QUEUE_BOT
                api = CiscoSparkAPI(DEV_QUEUE_BOT)

            logger.debug('Spark API initialized')

            data = data['data']
            me_id = api.people.me().id

            if data.get('personId') != me_id and \
                    ((data.get('mentionedPeople') and me_id in data['mentionedPeople']) or
                     data.get('roomType') == 'direct'):
                logger.debug(pprint.pformat(data))
                BOT = Bot(api, data)
                BOT.handle_data(data)

            return ''

        else:
            return 'NO STOP PLEASE STOP'
    except Exception as e:
        if not PRODUCTION:
            raise
        print(traceback.format_exc())
        logger.error(traceback.format_exc())
        return '500 Internal Server Error'
