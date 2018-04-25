import json
import os
import pprint
import datetime

from app import logger
from config import ADMINS_FILE, GLOBAL_ADMINS
from queuebot.people import PeopleManager


class AdminManager:
    def __init__(self, api, project, people_manager):
        self._api = api
        self._file = ADMINS_FILE.format(project)
        self._project = project
        self._displayName = self._api.people.me().displayName
        self._people = people_manager

        os.makedirs(os.path.dirname(os.path.realpath(self._file)), exist_ok=True)

        if not os.path.exists(self._file):
            self._admins = []
            self._save()
        else:
            self._admins = json.load(open(self._file, 'r'))

    def get_admins(self):
        return self._admins

    def is_admin(self, id, project=None):
        if not project:
            return id in GLOBAL_ADMINS + self._admins
        else:
            return id in json.load(open(ADMINS_FILE.format(project), 'r')) + GLOBAL_ADMINS

    def is_global_admin(self, id):
        return id in GLOBAL_ADMINS

    def _save(self):
        logger.debug(pprint.pformat(self._admins))
        json.dump(self._admins, open(self._file, 'w'), indent=4, separators=(',', ': '))

    def add_admin(self, id):
        logger.debug("Adding admin '" + id + "'")

        self._admins.append(id)

        if self._people.get_person(id):
            self._people.update_person(
                id=id,
                admin=True
            )
        self._save()

    def remove_admin(self, id):
        logger.debug("Removing admin '" + id + "'")

        self._admins = [i for i in self._admins if i != id]

        if self._people.get_person(id):
            self._people.update_person(
                id=id,
                admin=False
            )
        self._save()
