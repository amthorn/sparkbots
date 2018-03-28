from app import app
from cronbot import CronBot

@app.route('/cronbot', methods=['GET'])
def cron():
    print("HI")
    bot = CronBot()

@app.route('/queuebot', methods=['GET'])
def queue():
    return "QUEUE BOT SUCCESS"
