import json
import os
import pprint

from app import logger
from app.config import PEOPLE_FILE


class PeopleManager:
    def __init__(self, api, project):
        self._api = api
        self._file = PEOPLE_FILE
        self._project = project

        if not os.path.exists(self._file):
            self._people = []
        else:
            self._people = json.load(open(self._file, 'r'))

    def get_people(self):
        return [i for i in self._people if i['project'] == self._project]

    def get_person(self, id):
        for person in self._people:
            if id == person['sparkId'] and self._project == person['project']:
                return person
        else:
            return {}

    def _save(self):
        logger.debug(pprint.pformat(self._people))
        json.dump(self._people, open(self._file, 'w'), indent=4, separators=(',', ': '))

    def update_person(self, id, **kwargs):
        person = self.get_person(id=id)
        for key, value in kwargs.items():
            person[key] = value
        self._save()

    def add_person(self, data):
        person = self.get_person(id=data['personId'])
        if not person:
            api_person = self._api.people.get(data['personId'])
            logger.debug("Adding person '" + api_person.id + "'")

            person = {
                'sparkId': api_person.id,
                'displayName': api_person.displayName,
                'nickName': api_person.nickName,
                'lastName': api_person.lastName,
                'email': api_person.emails[0],
                'avatar': api_person.avatar,
                'project': self._project,
                'totalTimeInQueue': 0,  # microseconds
                'totalTimeAtHead': 0,  # microseconds
                'currentlyInQueue': False,  # microseconds
                'admin': False,
                'commands': 1,
                'number_of_times_in_queue': 0
            }
            self._people.append(person)
            self._save()
            return person
        else:
            logger.info("Person '" + data['personId'] + "' not added because they already exist")
            return person

    def remove_person(self, api_person):
        logger.debug("Checking if person '" + person.id + "' exists")
        for index, person in enumerate(self._people):
            if api_person.id == person['sparkId']:
                break
        else:
            return
        self._save()
