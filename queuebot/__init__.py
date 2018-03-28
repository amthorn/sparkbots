import datetime
import pickle
import os

from ciscosparkapi import CiscoSparkAPI
from config import QUEUE_BOT, LOG


class QueueBot():
    def __init__(self):
        self.api = CiscoSparkAPI(QUEUE_BOT)
        self.supported_commands = {
            'add me': self.add_me,
            'remove me': self.remove_me,
            'list': self.list_queue
        }
        if not os.path.exists(LOG):
            self.q = []
        else:
            self.q = pickle.load(open(LOG, 'rb'))

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
        person = self.api.people.get(data['personId'])
        self.create_message("Adding '"+ str(person.displayName) + "'", data['roomId'])
        self.enque(person)
        self.list_queue(data)

    def list_queue(self, data):
        if self.q:
            people = '- ' + ('\n- '.join([i['person'] for i in self.q]))
        else:
            people = 'There is no one in the queue'

        self.create_message(
            'Current queue is:\n\n' + people,
            data['roomId']
        )

    def remove_me(self, data):
        person = self.api.people.get(data['personId'])
        self.create_message("Removing '"+ str(person.displayName) + "'", data['roomId'])
        import pdb; pdb.set_trace()
        if not self.deque(person):
            self.create_message("ERROR: '" + str(person.displayName) + "' was not found in the queue")
        else:
            self.list_queue(data)

    def enque(self, person):
        self.q.append({
            'time': datetime.datetime.now(),
            'personId': person.id,
            'person': person.displayName
        })
        pickle.dump(self.q, open(LOG, 'wb'))
        return True

    def deque(self, person):
        for index, member in enumerate(self.q):
            if member['personId'] == person.id:
                break
        else:
            return False
        self.pop(index)
        pickle.dump(self.q, open(LOG, 'wb'))
        return True

