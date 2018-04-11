import json

from config import PROJECT_CONFIG, QUEUE_BOT
from ciscosparkapi import CiscoSparkAPI

api = CiscoSparkAPI(QUEUE_BOT)
message = 'I am going to be updating queuebot APRIL 11 around 8pm. Expect downtime for about an hour'

# I don't want to accidently run it.
if False:
    for room, project in json.load(open(PROJECT_CONFIG)).items():
            try:
                api.messages.create(
                    markdown=message,
                    roomId=room
                )
            except:
                pass
