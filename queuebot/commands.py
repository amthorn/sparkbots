import json
import os
import pprint
import datetime

from app import logger
from app.config import COMMANDS_FILE
from queuebot.people import PeopleManager


class CommandManager:
    def __init__(self, api, project):
        self._api = api
        self._file = COMMANDS_FILE
        self._project = project
        self._displayName = self._api.people.me().displayName
        self._people = PeopleManager(self._api, project=project)

        if not os.path.exists(self._file):
            self._commands = []
        else:
            self._commands = json.load(open(self._file, 'r'))

    def get_commands(self, project=None):
        if not project:
            return self._commands
        else:
            return [i for i in self._commands if i['project'] == project]

    def get_command(self, id, project):
        for command in self._commands:
            if id == command['sparkId'] and project == command['project']:
                return command
        else:
            return {}

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
            'project': project,
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
