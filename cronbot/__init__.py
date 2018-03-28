from ciscosparkapi import CiscoSparkAPI
from config import AVA_KEY

class CronBot:
    def __init__(self):
        self.ava = CiscoSparkAPI(AVA_KEY)
        import pdb; pdb.set_trace()