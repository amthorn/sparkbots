from ciscosparkapi import CiscoSparkAPI
from config import QUEUE_BOT

class QueueBot():
    def __init__(self):
        self.api = CiscoSparkAPI(QUEUE_BOT)

    def create_message(self, message):
        self.api.messages.create(message)

    def handle_data(self, data):
        import pdb; pdb.set_trace()
        if data:
            if self.api.people.me().id in data['mentionedPeople']:
                message_id = data['id']
                message_text = self.api.messages.get(message_id).text
                self.create_message(message_text)
            else:
                return ''
        else:
            self.create_message('Invalid POST request')
            return ''