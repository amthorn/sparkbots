import flask

from app import app
from cronbot import CronBot
from queuebot import QueueBot

@app.route('/cronbot', methods=['GET'])
def cron():
    print("HI")
    bot = CronBot()

@app.route('/queuebot', methods=['GET', 'POST'])
def queue():
    bot = QueueBot()
    bot.handle_data(flask.request.json.get('data'))
