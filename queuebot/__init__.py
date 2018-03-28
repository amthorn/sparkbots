from ciscosparkapi import CiscoSparkAPI
from config import QUEUE_BOT

class QueueBot():
    def __init__(self):
        self.api = CiscoSparkAPI(QUEUE_BOT)

    def create_message(self, message, roomId):
        self.api.messages.create(text=message, roomId=roomId)

    def handle_data(self, data):
        if data:
            if self.api.people.me().id in data['mentionedPeople']:
                message_id = data['id']
                message_text = self.api.messages.get(message_id).text
                import pdb; pdb.set_trace()
                # message_text = message_text.replace()
                self.create_message(message_text, data['roomId'])
            else:
                return ''
        else:
            return ''
