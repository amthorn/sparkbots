from ciscosparkapi import CiscoSparkAPI
from config import QUEUE_BOT

class QueueBot():
    def __init__(self):
        self.bot = CiscoSparkAPI(QUEUE_BOT)
        import pdb;
        pdb.set_trace()
        print()