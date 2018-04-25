import json
import os
import pprint
import datetime

from app import logger
from config import COMMANDS_FILE
from queuebot.people import PeopleManager


class CommandManager:
    def __init__(self, api, project, subproject, people_manager):
        self._api = api
        self._file = COMMANDS_FILE.format(project, '{}')
        self._project = project
        self._subproject = subproject
        self._people = people_manager
        self._commands = {}

        os.makedirs(os.path.dirname(os.path.dirname(os.path.realpath(self._file))), exist_ok=True)

    def get_commands(self):
        if not os.path.exists(self._file.format(self._subproject)):
            self._commands = []
        else:
            self._commands = json.load(open(self._file.format(self._subproject), 'r'))

        return self._commands

    def _save(self):
        logger.debug(pprint.pformat(self._commands))
        json.dump(self._commands, open(self._file.format(self._subproject), 'w'), indent=4, separators=(',', ': '))

    def add_command(self, data, person, parsed_command):
        api_message = self._api.messages.get(data['id'])
        logger.debug(api_message)
        logger.debug("Adding command '" + api_message.id + "'")

        self.get_commands()

        self._commands.append({
            'sparkId': api_message.id,
            'personId': api_message.personId,
            'displayName': person['displayName'],
            'roomId': api_message.roomId,
            'command': parsed_command,
            'timeIssued': str(datetime.datetime.now())
        })
        if self._people.get_person(id=api_message.personId):
            self._people.update_person(
                id=api_message.personId,
                commands=self._people.get_person(id=api_message.personId)['commands'] + 1
            )
        self._save()
        return api_message
