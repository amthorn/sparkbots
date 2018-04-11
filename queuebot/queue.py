import json
import os
import datetime
import pprint

from dateutil import parser
from collections import defaultdict
from app import logger, FORMAT_STRING, QUEUE_THRESHOLD, MAX_FLUSH_THRESHOLD
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
                'maxQueueDepthByHour': {},
                'minQueueDepthByHour': {},
                'minFlushTimeByHour': {},
                'maxFlushTimeByHour': {},
            }
        else:
            self._global_stats = json.load(open(self._global_stats_file, 'r'))

    def _save(self):
        logger.debug(pprint.pformat(self._q))
        json.dump(self._q, open(self._file, 'w'), indent=4, separators=(',', ': '))
        self._update_save_global_stats()

    def _update_save_global_stats(self):
        now = str(datetime.datetime.now())
        self._global_stats['historicalData']['queues'][now] = self._q
        self._global_stats['historicalData']['flush_times'][now] = self.get_estimated_flush_time()

        most_active = []
        most_activity = 0
        quickest_at_head = []
        quickest_head_time = -1

        for person in self._people.get_people():
            activity = self.get_queue_activity(person['sparkId'])
            current_head_time = person['totalTimeAtHead']

            if not most_active or most_activity < activity:
                most_active = [person['sparkId']]
                most_activity = activity
            elif most_activity == activity:
                most_active.append(person['sparkId'])
            if current_head_time:
                if quickest_head_time == -1 or current_head_time < quickest_head_time:
                    quickest_at_head = [person['sparkId']]
                    quickest_head_time = current_head_time
                elif current_head_time == quickest_head_time:
                    quickest_at_head.append(person['sparkId'])

        self._global_stats['mostActiveQueueUsers'] = most_active
        self._global_stats['historicalData']['mostActiveQueueUsers'][now] = most_active

        self._global_stats['quickestAtHeadUsers'] = quickest_at_head
        self._global_stats['historicalData']['quickestAtHeadUsers'][now] = quickest_at_head
        self._global_stats['historicalData']['largestQueueDepths'][now] = self._global_stats['largestQueueDepth']
        self._global_stats['historicalData']['largestQueueDepthTimes'][now] = self._global_stats['largestQueueDepthTime']

        q_depth = -1
        time = None
        self._global_stats['averageQueueDepthByHour'] = defaultdict(dict)


        for time, queue in self._global_stats['historicalData']['queues'].items():
            if self._global_stats['averageQueueDepthByHour'][str(parser.parse(time).hour)] == {}:
                self._global_stats['averageQueueDepthByHour'][str(parser.parse(time).hour)]['total'] = len(queue)
                self._global_stats['averageQueueDepthByHour'][str(parser.parse(time).hour)]['n'] = 1
            else:
                self._global_stats['averageQueueDepthByHour'][str(parser.parse(time).hour)]['total'] += len(queue)
                self._global_stats['averageQueueDepthByHour'][str(parser.parse(time).hour)]['n'] += 1

            self._global_stats['maxQueueDepthByHour'][str(parser.parse(time).hour)] = max(
                [len(queue), self._global_stats['maxQueueDepthByHour'].get(str(parser.parse(time).hour), 0)]
            )

            self._global_stats['minQueueDepthByHour'][str(parser.parse(time).hour)] = min(
                [len(queue), self._global_stats['minQueueDepthByHour'].get(str(parser.parse(time).hour),
                                                                           QUEUE_THRESHOLD + 1)]
            )

        self._global_stats['averageFlushTimeByHour'] = defaultdict(dict)

        for time, flush_time in self._global_stats['historicalData']['flush_times'].items():
            if self._global_stats['averageFlushTimeByHour'][str(parser.parse(time).hour)] == {}:
                self._global_stats['averageFlushTimeByHour'][str(parser.parse(time).hour)]['total'] = flush_time
                self._global_stats['averageFlushTimeByHour'][str(parser.parse(time).hour)]['n'] = 1
            else:
                self._global_stats['averageFlushTimeByHour'][str(parser.parse(time).hour)]['total'] += flush_time
                self._global_stats['averageFlushTimeByHour'][str(parser.parse(time).hour)]['n'] += 1

            self._global_stats['minFlushTimeByHour'][str(parser.parse(time).hour)] = min(
                [flush_time, self._global_stats['minFlushTimeByHour'].get(str(parser.parse(time).hour),
                                                                          MAX_FLUSH_THRESHOLD)]
            )
            self._global_stats['maxFlushTimeByHour'][str(parser.parse(time).hour)] = max(
                [flush_time, self._global_stats['maxFlushTimeByHour'].get(str(parser.parse(time).hour), 0)]
            )

        queue_depth_final = {}
        flush_time_final = {}
        previous_average = -1
        for i in range(24):
            if str(i) not in self._global_stats['averageQueueDepthByHour']:
                if any([self._global_stats['averageQueueDepthByHour'][j] for j in range(i + 1, 24)]):
                    queue_depth_final[str(i)] = previous_average if previous_average != -1 else 0
                else:
                    queue_depth_final[str(i)] = 0
            else:
                v = self._global_stats['averageQueueDepthByHour'][str(i)]
                queue_depth_final[str(i)] = round((v['total'] / v['n']) if v['n'] else 0, 2)
                previous_average = queue_depth_final[str(i)]

            if str(i) not in self._global_stats['averageFlushTimeByHour']:
                if any([self._global_stats['averageFlushTimeByHour'][j] for j in range(i + 1, 24)]):
                    flush_time_final[str(i)] = previous_average if previous_average != -1 else 0
                else:
                    flush_time_final[str(i)] = 0
            else:
                v = self._global_stats['averageFlushTimeByHour'][str(i)]
                flush_time_final[str(i)] = round((v['total'] / v['n']) if v['n'] else 0, 2)
                previous_average = flush_time_final[str(i)]

        self._global_stats['averageQueueDepthByHour'] = queue_depth_final
        self._global_stats['averageFlushTimeByHour'] = flush_time_final
        self._global_stats['largestQueueDepth'] = q_depth
        self._global_stats['largestQueueDepthHour'] = time

        json.dump(self._global_stats, open(self._global_stats_file, 'w'), indent=4, separators=(',', ': '))

    def get_queue(self):
        return self._q

    def get_member(self, id):
        for member in self._q:
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

    def add_to_queue(self, data, project):
        person = self._api.people.get(data['personId'])

        self.get_queue()
        if len(self.get_queue()) == QUEUE_THRESHOLD:
            return {}
        else:
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
            at_head = round((now - at_head_time).total_seconds())
        else:
            at_head = 0

        total = round((now - enqueued).total_seconds())

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
                                round((datetime.datetime.now() - time_enqueued).total_seconds())
            else:
                time_in_queue = person['totalTimeInQueue']

            return round(time_in_queue / person['number_of_times_in_queue'], 2)

    def get_average_time_at_queue_head(self, id):
        queue = self.get_queue()
        person = self._people.get_person(id=id)
        if person['number_of_times_in_queue'] == 0:
            return 0
        else:
            if len(queue) and self.get_head().get('personId') == person['sparkId']:
                time_at_head = parser.parse(self.get_head()['atHeadTime'])
                total_head = person['totalTimeAtHead'] + round((datetime.datetime.now() - time_at_head).total_seconds())
            else:
                total_head = person['totalTimeAtHead']

            return round(total_head / person['number_of_times_in_queue'], 2)

    def get_most_active(self):
        return [self._people.get_person(i) for i in self._global_stats['mostActiveQueueUsers']]

    def get_queue_activity(self, id):
        person = self._people.get_person(id)
        return len(person['added_to_queue']) + len(person['removed_from_queue'])

    def get_estimated_flush_time(self, id=None):
        if id:
            member = self.get_member(id)
            if member:
                if self.get_head().get('personId') == id:
                    average = self.get_average_time_at_queue_head(member['personId'])
                    return max([0, average - round(
                        (datetime.datetime.now() - parser.parse(self.get_head()['atHeadTime'])).total_seconds()
                    )])
                else:
                    return self.get_average_time_at_queue_head(member['personId'])
            else:
                # Member not in queue
                raise Exception("Member '" + str(id) + "' not in queue")
        else:
            # Get estimated wait time for full queue
            return sum(self.get_estimated_flush_time(i['personId']) for i in self.get_queue())

    def get_largest_queue_depth(self):
        return self._global_stats['largestQueueDepth'], self._global_stats['largestQueueDepthTime']

    def get_quickest_at_head(self):
        return [self._people.get_person(i) for i in self._global_stats['quickestAtHeadUsers']]

    def get_average_queue_depth_by_hour(self):
        return self._global_stats['averageQueueDepthByHour']

    def get_max_queue_depth_by_hour(self):
        return self._global_stats['maxQueueDepthByHour']

    def get_min_queue_depth_by_hour(self):
        return self._global_stats['minQueueDepthByHour']

    def get_min_flush_time_by_hour(self):
        return self._global_stats['minFlushTimeByHour']

    def get_max_flush_time_by_hour(self):
        return self._global_stats['maxFlushTimeByHour']

    def get_average_flush_time_by_hour(self):
        return self._global_stats['averageFlushTimeByHour']
