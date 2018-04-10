import json
import os
import pprint
import datetime

from app import logger
from config import COMMANDS_FILE
from queuebot.people import PeopleManager


class CommandManager:
    def __init__(self, api, project, people_manager):
        self._api = api
        self._file = COMMANDS_FILE.format(project)
        self._project = project
        self._displayName = self._api.people.me().displayName
        self._people = people_manager

        os.makedirs(os.path.dirname(os.path.realpath(self._file)), exist_ok=True)

        if not os.path.exists(self._file):
            self._commands = []
        else:
            self._commands = json.load(open(self._file, 'r'))

    def get_commands(self, project=None):
        return self._commands

    def _save(self):
        logger.debug(pprint.pformat(self._commands))
        json.dump(self._commands, open(self._file, 'w'), indent=4, separators=(',', ': '))

    def add_command(self, data, person, project):
        api_message = self._api.messages.get(data['id'])
        logger.debug(api_message)
        logger.debug("Adding command '" + api_message.id + "'")

        parsed_command = api_message.text.replace(self._displayName, "", 1).strip()

        self._commands.append({
            'sparkId': api_message.id,
            'personId': api_message.personId,
            'displayName': person['displayName'],
            'roomId': api_message.roomId,
            'command': parsed_command,
            'timeIssued': str(datetime.datetime.now())
        })
        if self._people.get_person(api_message.personId):
            self._people.update_person(
                id=api_message.personId,
                commands=self._people.get_person(id=api_message.personId)['commands'] + 1
            )
        self._save()
        return parsed_command, api_message



    # def remove_person(self, api_person, project):
    #     logger.debug("Checking if person '" + person.id + "' exists")
    #     for index, person in enumerate(self._people):
    #         if api_person.id == person['SparkId']:
    #             break
    #     else:
    #         return
    #
    #     self._people.pop(index)
    #     self._save()
