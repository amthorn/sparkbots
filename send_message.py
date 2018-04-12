import json

from config import PROJECT_CONFIG, QUEUE_BOT
from ciscosparkapi import CiscoSparkAPI

api = CiscoSparkAPI(QUEUE_BOT)
message = 'QueueBot is back up and on version 1.1.0; run "show release notes" for details.'

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
