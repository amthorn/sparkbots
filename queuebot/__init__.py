from ciscosparkapi import CiscoSparkAPI
from config import QUEUE_BOT

class QueueBot():
    def __init__(self):
        self.api = CiscoSparkAPI(QUEUE_BOT)
        self.supported_commands = [
            'add me',
            'remove me'
        ]

    def create_message(self, message, roomId):
        self.api.messages.create(text=message, roomId=roomId)

    def handle_data(self, data):
        if data:
            if self.api.people.me().id in data['mentionedPeople']:
                message_id = data['id']
                message_text = self.api.messages.get(message_id).text
                message_text = message_text.replace(self.api.people.me().displayName, "", 1).strip()

                if message_text.lower() not in self.supported_commands:
                    self.create_message(
                        "Unrecognized Command: '" + message_text.lower() + "'\n\n" +
                        "Please use one of:\n" + str('\n- '.join(self.supported_commands)),
                        data['roomId']
                    )
                else:
                    self.create_message(message_text, data['roomId'])
            else:
                return ''
        else:
            return ''
