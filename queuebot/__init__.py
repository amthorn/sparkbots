from ciscosparkapi import CiscoSparkAPI
from config import QUEUE_BOT

class QueueBot():
    def __init__(self):
        self.api = CiscoSparkAPI(QUEUE_BOT)
        self.supported_commands = {
            'add me': self.add_me,
            'remove me': self.remove_me
        }

    def create_message(self, message, roomId):
        self.api.messages.create(text=message, roomId=roomId)

    def handle_data(self, data):
        if data:
            if data.get('mentionedPeople') and self.api.people.me().id in data['mentionedPeople']:
                message_id = data['id']
                message_text = self.api.messages.get(message_id).text
                message_text = message_text.replace(self.api.people.me().displayName, "", 1).strip()

                if message_text.lower() not in self.supported_commands:
                    self.create_message(
                        "Unrecognized Command: '" + message_text.lower() + "'\n\n" +
                        "Please use one of:\n- " + str('\n- '.join(self.supported_commands)),
                        data['roomId']
                    )
                else:
                    self.supported_commands[message_text.lower()](data)
        return ''

    def add_me(self, data):
        import pdb; pdb.set_trace()
        self.create_message(message_text, data['roomId'])

    def remove_me(self, data):
        pass
