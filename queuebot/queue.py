import json
import os
import datetime
import pprint

from dateutil import parser
from app import logger, FORMAT_STRING
from config import QUEUE_FILE, PEOPLE_FILE, COMMANDS_FILE, GLOBAL_STATS_FILE
from queuebot.people import PeopleManager


class Queue:
    def __init__(self, api, project, people_manager):
        self._api = api
        self._file = QUEUE_FILE.format(project)
        self._global_stats_file = GLOBAL_STATS_FILE.format(project)
        self._people = people_manager

        os.makedirs(os.path.dirname(os.path.realpath(self._file)), exist_ok=True)

        if not os.path.exists(self._file):
            self._q = []
        else:
            self._q = json.load(open(self._file, 'r'))

        if not os.path.exists(self._global_stats_file):
            self._global_stats = {
                'historicalData': {},
                'mostActiveQueueUsers': [],
                'quickestAtHeadUsers': [],
                'largestQueueDepth': 0
            }
        else:
            self._global_stats = json.load(open(self._global_stats_file, 'r'))

    def _save(self):
        logger.debug(pprint.pformat(self._q))
        json.dump(self._q, open(self._file, 'w'), indent=4, separators=(',', ': '))
        self._update_save_global_stats()

    def _update_save_global_stats(self):
        self._global_stats['historicalData'][str(datetime.datetime.now())] = self._q

        most_active = []
        most_activity = 0
        quickest_at_head = []
        quickest_head_time = -1

        for person in self._people.get_people():
            activity = len(person['added_to_queue']) + len(person['removed_from_queue'])
            current_head_time = person['totalTimeAtHead']

            if not most_active or most_activity < activity:
                most_active = [person['sparkId']]
            elif most_activity == activity:
                most_active.append(person['sparkId'])

            if quickest_head_time == -1 or current_head_time < quickest_head_time:
                quickest_at_head = [person['sparkId']]
            elif current_head_time == quickest_head_time:
                quickest_at_head.append(person['sparkId'])

        self._global_stats['mostActiveQueueUsers'] = most_active
        self._global_stats['quickestAtHeadUsers'] = quickest_at_head
        self._global_stats['largestQueueDepth'] = max([len(i) for i in self._global_stats['historicalData'].values()])

        json.dump(self._global_stats, open(self._global_stats_file, 'w'), indent=4, separators=(',', ': '))

    def get_queue(self):
        return self._q

    def get_head(self):
        q = self.get_queue()
        return q[0] if len(q) else {}

    def get_queue_member(self, id):
        for member in self.get_queue():
            if member['personId'] == id:
                return member
        else:
            return {}

    def add_to_queue(self, data, project):
        person = self._api.people.get(data['personId'])

        self.get_queue()
        enqueued = str(datetime.datetime.now())

        self._q.append({
            'personId': data['personId'],
            'timeEnqueued': enqueued,
            'displayName': person.displayName,
            'atHeadTime': None if len(self._q) else str(datetime.datetime.now())
        })
        pickled_person = self._people.get_person(data['personId'])
        self._people.update_person(
            id=data['personId'],
            currentlyInQueue=True,
            number_of_times_in_queue=pickled_person['number_of_times_in_queue'] + 1,
            added_to_queue=pickled_person['added_to_queue'] + [enqueued]
        )
        self._save()
        return person

    def remove_from_queue(self, data):
        for index, member in enumerate(self.get_queue()):
            if member['personId'] == data['personId']:
                break
        else:
            return False

        member = self._q.pop(index)
        now = datetime.datetime.now()

        if len(self._q) and not self._q[0]['atHeadTime']:
            self._q[0]['atHeadTime'] = str(now)

        person = self._people.get_person(id=member['personId'])
        enqueued = parser.parse(member['timeEnqueued'])
        if member.get('atHeadTime'):
            at_head_time = parser.parse(member['atHeadTime'])
            at_head = (now - at_head_time).seconds
        else:
            at_head = 0

        total = (now - enqueued).seconds

        self._people.update_person(
            id=member['personId'],
            totalTimeInQueue=person['totalTimeInQueue'] + total,
            totalTimeAtHead=person['totalTimeAtHead'] + at_head,
            currentlyInQueue=False,
            removed_from_queue=person['removed_from_queue'] + [str(now)]
        )

        self._save()
        return True

    def get_average_time_in_queue(self, id):
        person = self._people.get_person(id=id)
        if person['number_of_times_in_queue'] == 0:
            return 0
        else:
            if person['currentlyInQueue']:
                time_enqueued = parser.parse(self.get_queue_member(person['sparkId'])['timeEnqueued'])
                time_in_queue = person['totalTimeInQueue'] + \
                                (datetime.datetime.now() - time_enqueued).seconds
            else:
                time_in_queue = person['totalTimeInQueue']

            return round(time_in_queue / person['number_of_times_in_queue'], 2)

    def get_average_time_at_queue_head(self, id):
        queue = self.get_queue()
        person = self._people.get_person(id=id)
        if person['number_of_times_in_queue'] == 0:
            return 0
        else:
            if len(queue) and self.get_head()['personId'] == person['sparkId']:
                time_enqueued = parser.parse(self.get_head()['atHeadTime'])
                total_head = person['totalTimeAtHead'] + (datetime.datetime.now() - time_enqueued).seconds
            else:
                total_head = person['totalTimeAtHead']

            return round(total_head / person['number_of_times_in_queue'], 2)