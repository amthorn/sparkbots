import json
import os
import datetime
import pprint
import statistics

from dateutil import parser
from collections import defaultdict
from app import logger, FORMAT_STRING, QUEUE_THRESHOLD, MAX_FLUSH_THRESHOLD
from config import QUEUE_FILE, PEOPLE_FILE, COMMANDS_FILE, GLOBAL_STATS_FILE
from queuebot.people import PeopleManager


class Queue:
    def __init__(self, api, project, subproject, people_manager):
        self._api = api
        self._file = QUEUE_FILE.format(project, subproject)
        self._global_stats_file = GLOBAL_STATS_FILE.format(project, subproject)
        self._people = people_manager
        self._project = project
        self._subproject = subproject

        os.makedirs(os.path.dirname(os.path.dirname(os.path.realpath(self._file))), exist_ok=True)

        self._get_latest_data()

    def _save(self):
        logger.debug(pprint.pformat(self._q))
        json.dump(self._q, open(self._file, 'w'), indent=4, separators=(',', ': '))
        self._update_save_global_stats()

    def _update_save_global_stats(self):
        now = str(datetime.datetime.now())
        queue = self.get_queue()
        self._global_stats['historicalData']['flush_times'][now] = self.get_estimated_flush_time()
        self._global_stats['historicalData']['queues'][now] = queue

        most_active = []
        most_activity = 0
        quickest_at_head = []
        quickest_head_time = -1

        self._global_stats['mostActiveQueueUsers'] = most_active
        self._global_stats['historicalData']['mostActiveQueueUsers'][now] = most_active

        self._global_stats['quickestAtHeadUsers'] = quickest_at_head
        self._global_stats['historicalData']['quickestAtHeadUsers'][now] = quickest_at_head
        self._global_stats['historicalData']['largestQueueDepths'][now] = self._global_stats['largestQueueDepth']
        self._global_stats['historicalData']['largestQueueDepthTimes'][now] = self._global_stats['largestQueueDepthTime']

        q_depth = -1
        q_depth_time = None
        self._global_stats['queueDepth'] = defaultdict(dict)
        self._global_stats['queueDepth']['hour'] = defaultdict(list)
        self._global_stats['queueDepth']['day'] = defaultdict(list)

        for time, queue in self._global_stats['historicalData']['queues'].items():
            self._global_stats['queueDepth']['hour'][str(parser.parse(time).hour)].append(len(queue))
            self._global_stats['queueDepth']['day'][str(parser.parse(time).weekday())].append(len(queue))

        self._global_stats['flushTime'] = defaultdict(dict)
        self._global_stats['flushTime']['hour'] = defaultdict(list)
        self._global_stats['flushTime']['day'] = defaultdict(list)

        for time, flush_time in self._global_stats['historicalData']['flush_times'].items():
            self._global_stats['flushTime']['hour'][str(parser.parse(time).hour)].append(flush_time)
            self._global_stats['flushTime']['day'][str(parser.parse(time).weekday())].append(flush_time)

        previous_average_hour = -1
        previous_average_day = -1

        for i in range(7):
            if str(i) not in self._global_stats['queueDepth']['day']:
                if any([self._global_stats['queueDepth']['day'][str(j)] for j in range(i + 1, 7)]):
                    self._global_stats['queueDepth']['day'][str(i)] = previous_average_day if previous_average_day != -1 else 0
                else:
                    self._global_stats['queueDepth']['day'][str(i)] = 0
            else:
                previous_average_day = self._global_stats['queueDepth']['day'][str(i)]

            if str(i) not in self._global_stats['flushTime']['day']:
                if any([self._global_stats['flushTime']['day'][str(j)] for j in range(i + 1, 7)]):
                    self._global_stats['flushTime']['day'][str(i)] = previous_average_day if previous_average_day != -1 else 0
                else:
                    self._global_stats['flushTime']['day'][str(i)] = 0
            else:
                previous_average_day = self._global_stats['flushTime']['day'][str(i)]

        for i in range(24):
            if str(i) not in self._global_stats['queueDepth']['hour']:
                if any([self._global_stats['queueDepth']['hour'][str(j)] for j in range(i + 1, 24)]):
                    self._global_stats['queueDepth']['hour'][str(i)] = previous_average_hour if previous_average_hour != -1 else 0
                else:
                    self._global_stats['queueDepth']['hour'][str(i)] = 0
            else:
                previous_average_hour = self._global_stats['queueDepth']['hour'][str(i)]

            if str(i) not in self._global_stats['flushTime']['hour']:
                if any([self._global_stats['flushTime']['hour'][str(j)] for j in range(i + 1, 24)]):
                    self._global_stats['flushTime']['hour'][str(i)] = previous_average_hour if previous_average_hour != -1 else 0
                else:
                    self._global_stats['flushTime']['hour'][str(i)] = 0
            else:
                previous_average_hour = self._global_stats['flushTime']['hour'][str(i)]

        self._global_stats['largestQueueDepth'] = q_depth
        self._global_stats['largestQueueDepthHour'] = q_depth_time

        json.dump(self._global_stats, open(self._global_stats_file, 'w'), indent=4, separators=(',', ': '))

    def _get_latest_data(self):
        if not os.path.exists(self._global_stats_file):
            self._global_stats = {
                'historicalData': {
                    'queues': {},
                    'flush_times': {},
                    'quickestAtHeadUsers': {},
                    'mostActiveQueueUsers': {},
                    'largestQueueDepths': {},
                    'largestQueueDepthTimes': {}
                },
                'mostActiveQueueUsers': [],
                'quickestAtHeadUsers': [],
                'largestQueueDepth': -1,
                'largestQueueDepthTime': None,
            }
        else:
            self._global_stats = json.load(open(self._global_stats_file, 'r'))

        if not os.path.exists(self._file):
            self._q = []
        else:
            self._q = json.load(open(self._file, 'r'))

    def get_queue(self):
        self._get_latest_data()
        return self._q

    def get_member(self, id):
        for member in self.get_queue():
            if member['personId'] == id:
                return member
        else:
            return {}

    def get_head(self):
        q = self.get_queue()
        return q[0] if len(q) else {}

    def get_queue_member(self, id):
        for member in self.get_queue():
            if member['personId'] == id:
                return member
        else:
            return {}

    def add_to_queue(self, data):
        person = self._api.people.get(data['personId'])

        self.get_queue()
        if len(self.get_queue()) == QUEUE_THRESHOLD:
            return {}
        else:
            enqueued = str(datetime.datetime.now())
            q_length = len(self.get_queue())

            self._q.append({
                'personId': data['personId'],
                'timeEnqueued': enqueued,
                'displayName': person.displayName,
                'atHeadTime': None if q_length else str(datetime.datetime.now())
            })
            pickled_person = self._people.get_person(id=data['personId'])
            self._people.update_person(
                id=data['personId'],
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
            at_head = round((now - at_head_time).total_seconds())
        else:
            at_head = 0

        total = round((now - enqueued).total_seconds())

        self._people.update_person(
            id=member['personId'],
            timesInQueue=person['timesInQueue'] + [total],
            timesAtHead=person['timesAtHead'] + [at_head],
            currentlyInQueue=False,
            removed_from_queue=person['removed_from_queue'] + [str(now)]
        )

        self._save()
        return True

    def get_average_time_in_queue(self, id):
        person = self._people.get_person(id=id)
        if not person['timesInQueue']:
            return 0
        else:
            if person['currentlyInQueue']:
                time_enqueued = parser.parse(self.get_queue_member(person['sparkId'])['timeEnqueued'])
                person['timesInQueue'].append(round((datetime.datetime.now() - time_enqueued).total_seconds()))

            return round(sum(person['timesInQueue']) / len(person['timesInQueue']), 2)

    def get_average_time_at_queue_head(self, id):
        queue = self.get_queue()
        person = self._people.get_person(id=id)

        if not person['timesInQueue']:
            return 0
        else:
            if len(queue) and self.get_head().get('personId') == person['sparkId']:
                time_at_head = parser.parse(self.get_head()['atHeadTime'])
                current = max([0, round((datetime.datetime.now() - time_at_head).total_seconds())])
                times_at_head = person['timesAtHead'] + ([current] if current else [])
            else:
                times_at_head = person['timesAtHead']

            return round(sum(times_at_head) / len(person['timesInQueue']), 2)

    def get_median_time_at_queue_head(self, id):
        queue = self.get_queue()
        person = self._people.get_person(id=id)

        if not person['timesInQueue']:
            return 0
        else:
            if len(queue) and self.get_head().get('personId') == person['sparkId']:
                time_at_head = parser.parse(self.get_head()['atHeadTime'])
                current = max([0, round((datetime.datetime.now() - time_at_head).total_seconds())])
                times_at_head = person['timesAtHead'] + ([current] if current else [])
            else:
                times_at_head = person['timesAtHead']

            return statistics.median(times_at_head)

    def get_most_active(self):
        return [self._people.get_person(i) for i in self._global_stats['mostActiveQueueUsers']]

    def get_queue_activity(self, id):
        person = self._people.get_person(id=id)
        return len(person['added_to_queue']) + len(person['removed_from_queue'])

    def get_estimated_flush_time(self, id=None):
        if id:
            member = self.get_member(id)
            if member:
                if self.get_head().get('personId') == id:
                    return self.get_median_time_at_queue_head(member['personId'])
                else:
                    location_in_queue = [i['personId'] for i in self.get_queue()].index(id)
                    partial_queue = self.get_queue()[:location_in_queue]
                    return sum(self.get_estimated_flush_time(i['personId']) for i in partial_queue) + \
                           self.get_median_time_at_queue_head(id)
            else:
                # Member not in queue
                raise Exception("Member '" + str(id) + "' not in queue")
        else:
            # Get estimated flush time for full queue
            if self.get_queue():
                return self.get_estimated_flush_time(self.get_queue()[-1]['personId'])
            else:
                return 0

    def get_estimated_wait_time(self, id=None):
        if id:
            return max([0, self.get_estimated_flush_time(id=id) - self.get_median_time_at_queue_head(id)])
        else:
            return self.get_estimated_flush_time()

    def get_largest_queue_depth(self):
        if self._global_stats['largestQueueDepth'] != -1:
            return self._global_stats['largestQueueDepth'], parser.parse(self._global_stats['largestQueueDepthHour'])
        else:
            return 0, datetime.datetime.now()

    def get_quickest_at_head(self):
        return [self._people.get_person(id=i) for i in self._global_stats['quickestAtHeadUsers']]

    def get_function_attribute_by_unit(self, function, attribute, unit):
        data = self._global_stats.get(attribute, {}).get(unit, {})
        for i in data:
            data[i] = function(i)
        return data