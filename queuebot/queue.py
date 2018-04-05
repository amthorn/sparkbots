import json
import os
import datetime
import pprint

from app import logger, FORMAT_STRING
from app.config import QUEUE_FILE, PEOPLE_FILE, COMMANDS_FILE
from queuebot.people import PeopleManager


class Queue:
    def __init__(self, api, project):
        self._api = api
        self._file = QUEUE_FILE.format(project)
        self._people = PeopleManager(self._api, project=project)

        if not os.path.exists(self._file):
            self._q = []
        else:
            self._q = json.load(open(self._file, 'r'))

    def _save(self):
        logger.debug(pprint.pformat(self._q))
        json.dump(self._q, open(self._file, 'w'), indent=4, separators=(',', ': '))

    def get_queue(self):
        return self._q

    def get_queue_member(self, id):
        for member in self._q:
            if member['personId'] == id:
                return member
        else:
            return {}

    def add_to_queue(self, data, project):
        person = self._api.people.get(data['personId'])

        self._q.append({
            'personId': data['personId'],
            'timeEnqueued': str(datetime.datetime.now()),
            'displayName': person.displayName,
            'atHeadTime': None if len(self._q) else str(datetime.datetime.now())
        })
        pickled_person = self._people.get_person(data['personId'])
        self._people.update_person(
            id=data['personId'],
            currentlyInQueue=True,
            number_of_times_in_queue=pickled_person['number_of_times_in_queue'] + 1
        )
        self._save()
        return person

    def remove_from_queue(self, data):
        for index, member in enumerate(self._q):
            if member['personId'] == data['personId']:
                break
        else:
            return False

        member = self._q.pop(index)

        if len(self._q) and not self._q[0]['atHeadTime']:
            self._q[0]['atHeadTime'] = str(datetime.datetime.now())

        person = self._people.get_person(id=member['personId'])
        enqueued = datetime.datetime.strptime(member['timeEnqueued'], "%Y-%m-%d %H:%M:%S.%f")
        at_head_time = datetime.datetime.strptime(member['atHeadTime'], "%Y-%m-%d %H:%M:%S.%f")
        now = datetime.datetime.now()
        total = (now - enqueued).seconds
        at_head = (now - at_head_time).seconds

        self._people.update_person(
            id=member['personId'],
            totalTimeInQueue=person['totalTimeInQueue'] + total,
            totalTimeAtHead=person['totalTimeAtHead'] + at_head,
            currentlyInQueue=False
        )

        self._save()
        return True
