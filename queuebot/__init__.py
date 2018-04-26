import datetime
import os
import json
import re
import requests
import csv
import numpy
import shutil
import random
import matplotlib
matplotlib.use('Agg')

from dateutil import parser
from matplotlib import pyplot
from contextlib import contextmanager
from queuebot.queue import Queue
from queuebot.people import PeopleManager
from queuebot.commands import CommandManager
from queuebot.admins import AdminManager
from queuebot.projects import ProjectManager
from app import app, logger, FORMAT_STRING, TIMEOUT, CSV_FILE_FORMAT, VERSION, RELEASED, AUTHOR, EMAIL, QUEUE_THRESHOLD, RELEASE_NOTES, PROJECT_STALE_SECONDS, RANDOM_EASTER_REJECTION, DEFAULT_SUBPROJECT
from config import PROJECT_CONFIG, GLOBAL_ADMINS, DATA_FOLDER
from queuebot.enum import COMMAND


class Bot():
    def __init__(self, api, data):
        self.api = api
        logger.debug("Initializing Project Manager")
        self.project = ProjectManager(self.api, roomId=data['roomId'])
        logger.debug("Initialized Project Manager")

        self.permitted_null_commands = [
            self.register_bot,
            self.create_new_project,
            self.show_release_notes_for,
            self.show_release_notes
        ]

        self.column_names = [
            'PERSON',
            'AVERAGE TIME IN QUEUE',
            'AVERAGE TIME AT QUEUE HEAD',
            'COMMANDS ISSUED',
            'NUMBER OF TIMES IN QUEUE',
            'TOTAL TIME IN QUEUE',
            'TOTAL TIME AT QUEUE HEAD',
        ]

        self.supported_commands = {
            'add me': self.add_me,
            'remove me': self.remove_me,
            'list': self.list_queue,
            'list for all subprojects': self.list_queue_all_subprojects,
            'help': self.help,
            'status': self.status,
            'how long': self.how_long,
            'about': self.about,
            'show subprojects': self.show_subprojects,
            'show version': self.show_version_number,
            'show all release notes': self.show_release_notes,
            'show release notes (.*)': self.show_release_notes_for,
        }
        logger.debug('supported commands:\n' + str(self.supported_commands.keys()))

        self.supported_admin_commands = {
            'show admin commands': self.show_admin_commands,
            'show admins': self.show_admins,
            'add admin (.*)': self.add_admin,
            'create new subproject (\w+)': self.create_new_subproject,
            'delete subproject (\w+)': self.delete_subproject,
            'remove admin (.*)': self.remove_admin,
            'register bot to project (\w+)': self.register_bot,
            'show registration': self.show_registration,
            'create new project (\w+)': self.create_new_project,
            'delete project': self.delete_project,
            'change default subproject to (\w+)': self.change_default_subproject,
            'show last (\d*) commands': self.show_command_history,
            'show people': self.show_people,
            'show all stats as csv': self.get_stats_csv,
            'show all stats as markdown': self.get_stats,
            'show stats for (.*)': self.get_stats_for,
            'add person (.*)': self.add_person,
            'remove person (.*)': self.remove_person,
            'show most active users': self.most_active_users,
            'show largest queue depth': self.largest_queue_depth,
            'show quickest users': self.quickest_at_head_user,
            'show (average|max|min) (queue depth|flush time) by (hour|day)': self.get_aggregate_stat_unit,
            'show strict regex': self.show_strict_regex,
            'set strict regex to (.*)': self.set_strict_regex,
            'delete last message': self.delete_last_message
        }
        logger.debug('supported admin commands:\n' + str(self.supported_admin_commands.keys()))

        self.supported_global_admin_commands = {
            'show projects': self.show_projects,
        }

        command_strings = ''

        for command, docstring in self._commands_with_help_string().items():
            docstring = self._clean_docstring(docstring)
            command_strings += '- **' + command + (('** (' + docstring + ')\n') if docstring else '**\n')

        self.help_string = \
            "This bot is to be used to manage a queue for a given team. " \
            "It can be used to get statistical information as well as manage an individual queue.\n\n" \
            "This QueueBot is registered to '" + str(self.project.get_project()) + "'\n\n" \
            "You can end any command with the suffix '**for subproject [subproject name]**' to apply " \
            "that command to the given subproject. Available commands are:\n\n" + command_strings + \
            "\nFor admins, use 'show admin commands' to see a list of admin commands"

        self.about_string = \
            "This bot is to be used to manage a queue for a given team. " \
            "It can be used to get statistical information as well as manage an individual queue.\n" \
            "\n" \
            "This QueueBot is registered to '" + str(self.project.get_project()) + "'\n" \
            "\n" \
            "Version: **" + str(VERSION) + "**\n\n" \
            "Released: " + str(RELEASED) + "\n\n" \
            "Author: " + str(AUTHOR) + " (" + str(EMAIL) + ")"

    def delete_last_message(self, data):
        my_id = self.api.people.me().id
        for message in self.api.messages.list(roomId=data['roomId']):
            if message.personId == my_id:
                self.api.messages.delete(message.id)
                break

    def _clean_docstring(self, docstring):
        if docstring:
            docstring = docstring.strip('\n ')
            while '  ' in docstring:
                docstring = re.sub('  ', ' ', docstring)
            docstring = docstring.replace('\n', '')
            return docstring

    def list_queue_all_subprojects(self, data):
        """
        shows the list of all subproject queues
        """
        for subproject in self.project.get_subprojects():
            self.initialize_data(project=self.project.get_project(), subproject=subproject)
            self.list_queue(data)

    def show_strict_regex(self, data):
        self.create_message(
            'Strict regex for project "' + self.project.get_project() + '" is: ' + str(self.project.strict_regex),
            roomId=data['roomId']
        )

    def set_strict_regex(self, data):
        value = re.search('set strict regex to (.*)', self.message_text).group(1)
        self.project.strict_regex = bool(value.title() != 'False')
        self.show_strict_regex(data)

    def _commands_with_help_string(self):
        return {k: v.__doc__ for k, v in sorted(self.supported_commands.items())}

    def _admin_commands_with_help_string(self):
        return {k: v.__doc__ for k, v in sorted(self.supported_admin_commands.items())}

    def status(self, data):
        """
        Shows the current status of queuebot
        """
        message = "STATUS: Thank you for asking, nobody really asks anymore. " \
                  "I guess I'm okay, I just have a lot going on, you know? I'm " \
                  "supposed to be managing all the queues for people and it's so " \
                  "hard because I have to be constantly paying attention to every " \
                  "chatroom at all hours of the day, I get no sleep and my " \
                  "social life has plumetted. But I guess I'm:\n" \
                  "\n" \
                  "200 OK"

        self.create_message(
            message,
            roomId=data['roomId']
        )

    def get_stats_for(self, data):
        """
        Returns a markdown table of global statistics for the given statistic
        """
        stat = re.search('show stats for (.*)', self.message_text).group(1)
        if stat.upper() not in self.column_names:
            self.create_message(
                "Column '" + str(stat) + "' is not a valid column. Try one of: " + ', '.join(self.column_names),
                roomId=data['roomId']
            )
        else:
            self.create_message(
                'Showing stats for subproject "' + str(self.subproject) + '"\n\n' + self._create_markdown_table(self._get_stats(stat.upper())),
                roomId=data['roomId']
            )

    def get_stats(self, data):
        """
        Returns a markdown table of global statistics for the project
        """
        self.create_message(
            'Showing stats for subproject "' + str(self.subproject) + '"\n\n' +
            self._create_markdown_table(self._get_stats()),
            roomId=data['roomId']
        )

    def _create_markdown_table(self, raw_dict):
        "Requires dictionary of lists"
        message = "```\n"
        widths = {}
        column_length = 0
        dictionary = {}

        for column in raw_dict:
            if raw_dict[column]:
                column_length = len(raw_dict[column])
                dictionary[column] = raw_dict[column]
                widths[column] = max([len(str(i)) for i in raw_dict[column]] + [len(column)])

        person = dictionary['PERSON']
        del dictionary['PERSON']

        for index, column in enumerate(['PERSON'] + sorted(dictionary)):
            message += column.center(widths[column], ' ') + (" | " if index < len(dictionary) else '\n')

        for index in range(column_length):
            message += str(person[index]).center(widths['PERSON'], ' ') + " | "
            for column_index, column in enumerate(sorted(dictionary)):
                message += str(dictionary[column][index]).center(widths[column], ' ') + \
                           (" | " if column_index < len(dictionary) - 1 else '\n')

        return message

    def _get_stats(self, target=None):
        people = self.people.get_people()
        queue = self.q.get_queue()
        stats = {i: [] for i in self.column_names}

        for person in people:
            stats['PERSON'].append(person['displayName'])
            if not target or target == 'TOTAL TIME IN QUEUE':
                if person['currentlyInQueue']:
                    time_enqueued = parser.parse(self.q.get_queue_member(person['sparkId'])['timeEnqueued'])
                    stats[target or 'TOTAL TIME IN QUEUE'].append(str(sum(person['timesInQueue']) + \
                                    round((datetime.datetime.now() - time_enqueued).total_seconds())) + ' seconds')
                else:
                    stats[target or 'TOTAL TIME IN QUEUE'].append(str(sum(person['timesInQueue'])) + ' seconds')
            if not target or target == 'TOTAL TIME AT QUEUE HEAD':
                if len(queue) and queue[0]['personId'] == person['sparkId']:
                    time_enqueued = parser.parse(queue[0]['atHeadTime'])
                    stats[target or 'TOTAL TIME AT QUEUE HEAD'].append(str(sum(person['timesInQueue']) +
                                         round((datetime.datetime.now() - time_enqueued).total_seconds())) + ' seconds')
                else:
                    stats[target or 'TOTAL TIME AT QUEUE HEAD'].append(str(sum(person['timesInQueue'])) + ' seconds')

            if not target or target == 'AVERAGE TIME IN QUEUE':
                stats[target or 'AVERAGE TIME IN QUEUE'].append(
                    str(self.q.get_average_time_in_queue(id=person['sparkId'])) + ' seconds'
                )
            if not target or target == 'AVERAGE TIME AT QUEUE HEAD':
                stats[target or 'AVERAGE TIME AT QUEUE HEAD'].append(
                    str(self.q.get_average_time_at_queue_head(id=person['sparkId'])) + ' seconds'
                )
            if not target or target == 'COMMANDS ISSUED':
                stats[target or 'COMMANDS ISSUED'].append(str(person['commands']))
            if not target or target == 'NUMBER OF TIMES IN QUEUE':
                stats[target or 'NUMBER OF TIMES IN QUEUE'].append(str(len(person['timesInQueue'])))
        return stats

    def show_projects(self, data):
        message = 'Registered projects are:\n\n'

        for project in set([i[0] for i in self.project.config]):
            all_commands = self.project.get_commands(project, subproject=None)
            last_command = max([parser.parse(i['timeIssued']) for i in all_commands])
            stale = " **STALE**" if (datetime.datetime.now() - last_command).total_seconds() > PROJECT_STALE_SECONDS else ''
            message += '- ' + str(project) + ' (' + str(len([i for i in self.project.config if i[0] == project])) + \
                       ' room/s; ' + str(len(self.project.get_subprojects(project=project))) + ' subproject/s; ' + str(last_command) + ')' + stale + '\n'

        self.create_message(
            message,
            roomId=data['roomId']
        )

    def create_message(self, message, roomId):
        logger.debug("Sending Message '" + message + "' to room '" + roomId + "' ")
        self.api.messages.create(markdown=message, roomId=roomId)
        logger.debug("Message Sent")

    def arg_exists(self, string):
        for command in self.supported_commands:
            executed_command = ("^" + command + "$") if self.project.strict_regex else command
            if re.search(executed_command, string.lower()):
                logger.debug("Found function for command '" + str(string) + "'")
                return self.supported_commands[command]
        else:
            logger.debug("No function found for command '" + str(string) + "'")
            return None

    def admin_arg_exists(self, string):
        for command in self.supported_admin_commands:
            executed_command = ("^" + command + "$") if self.project.strict_regex else command
            if re.search(executed_command, string.lower()):
                logger.debug("Found admin function for command '" + str(string) + "'")
                return self.supported_admin_commands[command]
        else:
            logger.debug("No admin function found for command '" + str(string) + "'")
            return None

    def global_admin_arg_exists(self, string):
        for command in self.supported_global_admin_commands:
            executed_command = ("^" + command + "$") if self.project.strict_regex else command
            if re.search(executed_command, string.lower()):
                logger.debug("Found global admin function for command '" + str(string) + "'")
                return self.supported_global_admin_commands[command]
        else:
            logger.debug("No global admin function found for command '" + str(string) + "'")
            return None

    def _rejection_message(self, data):
        self.api.messages.create(
            files=['queuebot/rejection_pic.jpg'],
            roomId=data['roomId']
        )

    def initialize_data(self, project, subproject):
        self.subproject = subproject

        logger.debug("Initializing People Manager")
        self.people = PeopleManager(
            self.api,
            project=project,
            subproject=subproject
        )
        logger.debug("Initialized People Manager")

        logger.debug("Initializing Admin Manager")
        self.admins = AdminManager(
            self.api,
            project=project,
            people_manager=self.people
        )
        logger.debug("Initialized Admin Manager")

        logger.debug("Initializing Queue")
        self.q = Queue(
            self.api,
            project=project,
            people_manager=self.people,
            subproject=subproject
        )
        logger.debug("Initialized Queue")

        logger.debug("Initializing Command Manager")
        self.commands = CommandManager(
            self.api,
            project=project,
            people_manager=self.people,
            subproject=subproject
        )
        logger.debug("Initialized Command Manager")

    def handle_data(self, data):
        self.message_text = self.api.messages.get(data['id']).text.replace(self.api.people.me().displayName, "", 1).strip()

        pattern = re.search('.*\sfor\ssubproject\s(\w+)', self.message_text)
        self.message_text = re.sub('\s+for\ssubproject\s(\w+)', '', self.message_text)

        pattern = getattr(pattern, 'groups', lambda: None)()

        if self.project.get_project() and pattern and len(pattern) == 1 and pattern[0]:
            self.subproject = pattern[0].upper()
        else:
            self.subproject = self.project.get_default_subproject()
            if not self.subproject:
                self.create_message(
                    'There is no default subproject for project "' + str(self.project.get_project()) +
                    '". You must set a default subproject or specify a subproject.',
                    roomId=data['roomId']
                )
                return
            else:
                self.subproject = self.subproject.upper()

        if self.project.get_project() and self.subproject not in self.project.get_subprojects():
            self.create_message(
                '"' + str(self.subproject) + '" is not a subproject on project "' + str(self.project.get_project()) + '"',
                roomId=data['roomId']
            )
        else:
            self.initialize_data(project=self.project.get_project(), subproject=self.subproject)

            person = self.people.add_person(data)
            self.commands.add_command(
                data=data,
                person=person,
                parsed_command=self.message_text
            )

            if self.message_text.lower() == 'help':
                self.supported_commands['help'](data)
            elif self.message_text.lower() == 'cat fact':
                if random.random() <= RANDOM_EASTER_REJECTION:
                    self._rejection_message(data)
                else:
                    self.create_message(
                        requests.get('https://catfact.ninja/fact').json()['fact'],
                        roomId=data['roomId']
                    )
            elif self.message_text.lower() == 'pun':
                if random.random() <= RANDOM_EASTER_REJECTION:
                    self._rejection_message(data)
                else:
                    self.create_message(
                        requests.get('https://icanhazdadjoke.com/', headers={'Accept': 'application/json'}).json()['joke'],
                        roomId=data['roomId']
                    )
            elif self.global_admin_arg_exists(self.message_text):
                if self.admins.is_global_admin(id=data['personId']):
                    self.global_admin_arg_exists(self.message_text)(data)
                else:
                    self.create_message(
                        'You are not registered as a global admin.',
                        roomId=data['roomId']
                    )
            elif self.admin_arg_exists(self.message_text):
                if self.admins.is_admin(id=data['personId']):
                    function = self.admin_arg_exists(self.message_text)
                    if function == self.register_bot or function == self.create_new_project or self.project.get_project():
                        function(data)
                    else:
                        message = "QueueBot is not registered to a project! Ask an admin to register this bot"
                        self.create_message(message, data['roomId'])
                else:
                    function = self.admin_arg_exists(self.message_text)
                    if not self.project.get_project() and function in self.permitted_null_commands:
                        function(data)
                    else:
                        self.create_message(
                            'You are not registered as an admin.',
                            roomId=data['roomId']
                        )
            else:
                function = self.arg_exists(self.message_text)

                if not self.project.get_project() and function in self.permitted_null_commands:
                    function(data)
                elif not function:
                    self.no_command_found(data)
                elif not self.project.get_project():
                    message = "QueueBot is not registered to a project! Ask an admin to register this bot"
                    self.create_message(message, data['roomId'])
                else:
                    function(data)

    def no_command_found(self, data):
        self.create_message(
            "Unrecognized Command: '" + self.message_text.lower() + "'\n\n" +
            "Please use one of:\n- " + str('\n- '.join(sorted(self.supported_commands))),
            data['roomId']
        )

    def add_me(self, data):
        """
        Adds you to the back of the queue
        """
        logger.debug("Executing add me")
        person = self.q.add_to_queue(data)
        if not person:
            self.create_message(
                'Failed to add to queue because queue is already at maximum of "' + str(QUEUE_THRESHOLD) + '"',
                roomId=data['roomId']
            )
        else:
            self.list_queue(data, after=COMMAND.ADD, person=person)

    def create_new_subproject(self, data):
        subproject = re.search('create new subproject (\w+)', self.message_text).group(1).upper()
        self.project.create_subproject(name=subproject)
        self.create_message(
            'Successfully created new subproject "' + str(subproject) + '"',
            roomId=data['roomId']
        )
        self.show_subprojects(data)

    def delete_subproject(self, data):
        subproject = re.search('delete subproject (\w+)', self.message_text).group(1).upper()
        if subproject != self.project.get_default_subproject():
            self.project.delete_subproject(name=subproject)
            self.create_message(
                'Successfully deleted subproject "' + str(subproject) + '"',
                roomId=data['roomId']
            )
            self.show_subprojects(data)
        else:
            self.create_message(
                'You cannot delete the default subproject.',
                roomId=data['roomId']
            )

    def change_default_subproject(self, data):
        subproject = re.search('change default subproject to (\w+)', self.message_text).group(1).upper()
        if subproject == self.project.get_default_subproject():
            self.create_message(
                'Default subproject is already set to "' + str(subproject)  +'"',
                roomId=data['roomId']
            )
        elif subproject not in self.project.get_subprojects():
            self.create_message(
                'Subproject "' + str(subproject) + '" does not exist on project "' + str(self.project.get_project()) + '"',
                roomId=data['roomId']
            )
        else:
            self.project.set_default_subproject(subproject)
            self.create_message(
                'Default subproject changed to "' + str(subproject)  +'"',
                roomId=data['roomId']
            )
            self.show_subprojects(data)


    def show_subprojects(self, data):
        """
        Shows a list of all subprojects with default subproject marked as DEFAULT
        """
        message = 'Subprojects for project "' + str(self.project.get_project()) + '" are:\n\n'
        default = self.project.get_default_subproject()
        for subproject in self.project.get_subprojects():
            message += '- ' + str(subproject) + (' (DEFAULT)\n' if default == subproject else '\n')
        self.create_message(
            message,
            roomId=data['roomId']
        )


    def list_queue(self, data, after=COMMAND.NONE, person=None):
        """
        Shows the queue without mutating it
        """
        logger.debug("Executing list queue")

        queue = self.q.get_queue()
        if queue:
            people = ''
            for index, member in enumerate(queue):
                people += str(index + 1) + '. ' + self.format_person(member) + '\n'
        else:
            people = 'There is no one in the queue'
        if after == COMMAND.ADD and person:
            message = 'Adding "'+ str(person.displayName) + '"\n\n'
        elif after == COMMAND.REMOVE and person:
            message = 'Removing "'+ str(person.displayName) + '"\n\n'
        else:
            message = ''

        if after == COMMAND.REMOVE and self.q.get_head():
            person = self.q.get_head()
            tag = "<@personId:"+ person['personId'] + "|" + str(person['displayName']) + ">, you're at the front of the queue!"
        else:
            tag = None

        message += 'Current queue on subproject "' + str(self.subproject) + '" is:\n\n' + people + '\n\n' + \
                   self._how_long() + ('\n\n' + tag if tag else '')

        self.create_message(
            message,
            data['roomId']
        )

    def remove_me(self, data):
        """
        Removes the first occurence of you from the queue
        """
        logger.debug("Executing remove me")
        person = self.api.people.get(data['personId'])
        if not self.q.remove_from_queue(data):
            self.create_message("ERROR: '" + str(person.displayName) + "' was not found in the queue", data['roomId'])
        else:
            self.list_queue(data, after=COMMAND.REMOVE, person=person)

    def format_person(self, person):
        formatted_date = parser.parse(person['timeEnqueued'])
        return person['displayName'] + " (" + formatted_date.strftime(FORMAT_STRING) + ")"

    def show_admins(self, data):
        """
        Shows all the admins for the current project
        """
        admin_names = [self.api.people.get(i).displayName for i in self.admins.get_admins()]
        global_admin_names = [self.api.people.get(i).displayName for i in GLOBAL_ADMINS]
        global_admins_nice = '- '.join([(i + ' (global)\n') for i in global_admin_names])
        admins_nice = '- '.join([(i + '\n') for i in set(admin_names) - set(global_admin_names)])

        if global_admins_nice:
            admins_nice += ('\n- ' if admins_nice else '') + global_admins_nice

        self.create_message(
            "Admins for '" + str(self.project.get_project()) + "' are:\n- " + admins_nice,
            roomId=data['roomId']
        )

    def help(self, data):
        """
        Displays a brief overview of queuebot and displays available user commands and their descriptions
        """
        self.create_message(
            self.help_string,
            data['roomId']
        )

    def show_admin_commands(self, data):
        """
        Displays all the available commands available to only admins
        """
        command_strings = ''

        for command, docstring in self._admin_commands_with_help_string().items():
            docstring = self._clean_docstring(docstring)
            command_strings += '- **' + command.replace("*", "\*") + (('** (' + docstring + ')\n') if docstring else '**\n')

        self.create_message(
            'Admin commands can be used in any room but are only accessible by an admin.\n\n'
            'Available admin commands are:\n' + command_strings,
            roomId=data['roomId']
        )

    def register_bot(self, data):
        """
        Registers the room to the given project case-insensitive string.
        The same project can be registered to multiple rooms.
        But one room cannot be registered to multiple bots. Errors if the project doesn't exist or the user
        is not an admin on the target project
        """
        project = re.search('register bot to project (\w+)', self.message_text).group(1)
        if project.upper() in self.project.get_projects():
            if self.admins.is_admin(data['personId']):
                success, message = self.project.register_room_to_project(project, data['roomId'])
                if not success:
                    self.create_message(
                        message,
                        roomId=data['roomId']
                    )
                else:
                    self.create_message(
                        'Successfully registered bot to project "' + str(self.project.get_project()) + '"',
                        roomId=data['roomId']
                    )
            else:
                self.create_message(
                    'ERROR: You are not registered as an admin on project "' + str(project.upper()) + '"',
                    roomId=data['roomId']
                )
        else:
            self.create_message(
                'ERROR: project "' + str(project.upper()) + '" has not been created.',
                roomId=data['roomId']
            )

    def delete_project(self, data):
        """
        Deletes the current project; Cannot be undone
        """
        project = self.project.get_project()
        self.project.delete_project()
        self.create_message(
            "Successfully deleted project '" + project + "'",
            roomId=data['roomId']
        )

    def create_new_project(self, data):
        """
        Creates a new project with the given case-insensitive string, adds the user as an admin to that project,
        and registers the room to that project. Errors if the project already exists.
        """
        from config import ADMINS_FILE
        project = re.search('create new project (\w+)', self.message_text).group(1)

        success = self.project.create_new_project(project, roomId=data['roomId'])
        if not success:
            self.create_message(
                "ERROR: project '" + str(project.upper()) + "' already exists.",
                roomId=data['roomId']
            )
        else:
            self.create_message(
                "Created new project '" + str(project.upper()) + "'.",
                roomId=data['roomId']
            )

            self.admins._project = project
            self.admins.add_admin(data['personId'])

            success, message = self.project.register_room_to_project(project, roomId=data['roomId'])
            if not success:
                # Should never hit this line
                self.create_message(
                    message,
                    roomId=data['roomId']
                )
            else:
                self.header_string = "QueueBot: '" + str(self.project.get_project()) + "'"
                self.create_message(
                    "Registered bot to project '" + str(self.project.get_project()) + "'",
                    roomId=data['roomId']
                )

    def show_registration(self, data):
        """
        Shows the project that the current room is registered to
        """
        self.create_message(
            "QueueBot registration: " + str(self.project.get_project()),
            data['roomId']
        )
        self.show_subprojects(data)

    def show_command_history(self, data):
        """
        Shows the last X commands that were issued on this project where X is a non-negative integer
        """
        number = int(re.search('show last (\d*) commands', self.message_text).group(1))
        commands = self.commands.get_commands()
        command_string = ''
        for index, command in enumerate(commands[::-1]):
            if index >= number:
                break
            time = parser.parse(command['timeIssued'])
            command_string += str(index + 1) + '. ' + command['command'] + ' (' + str(command['displayName']) + \
                              ' executed at ' + str(time.strftime(FORMAT_STRING)) + ')\n'

        self.create_message(
            'Last ' + str(number) + ' commands for subproject "' + str(self.subproject) + '" are:\n' + command_string,
            roomId=data['roomId']
        )

    def add_person(self, data):
        """
        Adds the tagged person to the back of the queue
        """
        tagged = set(data['mentionedPeople']) - {self.api.people.me().id}
        if not tagged:
            self.create_message(
                "Nobody was tagged to be added. Please tag who you would like to add",
                roomId=data['roomId']
            )
        elif len(tagged) > 1:
            self.create_message(
                "Too many people were tagged. Please only tag one person at a time to be added",
                roomId=data['roomId']
            )
        else:
            person_data = {'personId': tagged.pop()}
            person = self.people.add_person(person_data)
            logger.debug("Executing add person")
            person = self.q.add_to_queue(person_data)
            if not person:
                self.create_message(
                    'Failed to add to queue because queue is already at maximum of "' + str(QUEUE_THRESHOLD) + '"',
                    roomId=data['roomId']
                )
            else:
                self.list_queue(data, after=COMMAND.ADD, person=person)

    def remove_person(self, data):
        """
        Removes the first occurence of the tagged person
        """
        tagged = set(data['mentionedPeople']) - {self.api.people.me().id}
        if not tagged:
            self.create_message(
                "Nobody was tagged to be removed. Please tag who you would like to remove",
                roomId=data['roomId']
            )
        elif len(tagged) > 1:
            self.create_message(
                "Too many people were tagged. Please only tag one person at a time to be removed",
                roomId=data['roomId']
            )
        else:
            person_data = {'personId': tagged.pop()}
            logger.debug("Executing remove me")
            person = self.api.people.get(person_data['personId'])
            if not self.q.remove_from_queue(person_data):
                self.create_message("ERROR: '" + str(person.displayName) + "' was not found in the queue", data['roomId'])
            else:
                self.list_queue(data, after=COMMAND.REMOVE, person=person)

    def add_admin(self, data):
        """
        Adds the tagged person as an admin for the current project
        """
        tagged = set(data['mentionedPeople']) - {self.api.people.me().id}

        if not tagged:
            self.create_message(
                "Nobody was tagged to be added. Please tag who you would like to add",
                roomId=data['roomId']
            )
        elif len(tagged) > 1:
            self.create_message(
                "Too many people were tagged. Please only tag one person at a time to be added",
                roomId=data['roomId']
            )
        else:
            person = self.api.people.get(tagged.pop())
            if person and person.id not in self.admins.get_admins():
                self.admins.add_admin(person.id)
                self.create_message(
                    "Added '" + str(person.displayName) + "' as an admin.",
                    roomId=data['roomId']
                )
                self.show_admins(data)
            elif person:
                self.create_message(
                    "'" + str(person.displayName) + "' is already an admin on this project",
                    roomId=data['roomId']
                )
            else:
                # This line should be unreachable.
                self.create_message(
                    "No person with id '" + str(person.id) + "' exists.",
                    roomId=data['roomId']
                )

    def remove_admin(self, data):
        """
        Removes the tagged person as an admin for the current project
        """
        tagged = set(data['mentionedPeople']) - {self.api.people.me().id}

        if not tagged:
            self.create_message(
                "Nobody was tagged to be removed. Please tag who you would like to remove",
                roomId=data['roomId']
            )
        elif len(tagged) > 1:
            self.create_message(
                "Too many people were tagged. Please only tag one person at a time to be removed",
                roomId=data['roomId']
            )
        else:
            person = self.api.people.get(tagged.pop())
            if person and person.id in self.admins.get_admins():
                self.admins.remove_admin(person.id)

                self.create_message(
                    "Removed '" + str(person.displayName) + "' as an admin.",
                    roomId=data['roomId']
                )
                self.show_admins(data)
            elif person:
                self.create_message(
                    "'" + str(person.displayName) + "' is not an admin on this project",
                    roomId=data['roomId']
                )
            else:
                # This line should be unreachable
                self.create_message(
                    "No person with id '" + str(person.id) + "' exists.",
                    roomId=data['roomId']
                )

    def show_people(self, data):
        """
        Shows the names of all the people that have issued a command to queuebot on this project
        """
        people_on_project = self.people.get_people()
        display = 'All people that have used this bot for subproject "' + str(self.subproject) + \
                  '" on project "' + str(self.project.get_project()) + '" are:\n'
        if people_on_project:
            for index, person in enumerate(people_on_project):
                display += str(index + 1) + ". " + person['displayName'] + '\n'
        else:
            # This line is likely unreachable.
            display += 'There are no people that have used this bot for this project/subproject'

        self.create_message(display, roomId=data['roomId'])

    def get_stats_csv(self, data):
        """
        Returns a CSV file attachment containing global statistics for the project
        """
        stats = self._get_stats()
        rows = [list(stats.keys())] + [list(i) for i in zip(*stats.values())]
        with open(CSV_FILE_FORMAT.format(self.project.get_project(), self.subproject), 'w') as csvfile:
            spamwriter = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            for row in rows:
                spamwriter.writerow(row)
        self.api.messages.create(
            markdown="Here are all the stats for subproject '" + str(self.subproject) + "' on project '" + str(self.project.get_project()) + "' as a csv",
            files=[CSV_FILE_FORMAT.format(self.project.get_project(), self.subproject)],
            roomId=data['roomId']
        )
        os.remove(CSV_FILE_FORMAT.format(self.project.get_project(), self.subproject))

    def _make_time_pretty(self, seconds):
        return str(datetime.timedelta(seconds=seconds))

    def _how_long(self, personId=None):
        seconds = 0

        if not personId or not self.q.get_member(personId):
            flush_time = self.q.get_estimated_wait_time()

            if len(self.q.get_queue()) == 1:
                people_string = 'is 1 person'
            else:
                people_string = 'are ' + str(len(self.q.get_queue())) + ' people'

            return 'Given that there ' + people_string + ' in the queue. ' \
                                                              'Estimated wait time from the back of the queue is:\n\n' + \
                   str(self._make_time_pretty(flush_time))
        else:
            flush_time = self.q.get_estimated_wait_time(personId)
            location_in_queue = [i['personId'] for i in self.q.get_queue()].index(personId)

        if location_in_queue == 1:
            people_string = 'is 1 person'
        else:
            people_string = 'are ' + str(location_in_queue) + ' people'

        return 'Given that there ' + people_string + ' ahead of you. Estimated wait time for "' + \
                   self.people.get_person(personId)['displayName'] + '" is:\n\n' + \
                   str(self._make_time_pretty(flush_time))

    def how_long(self, data):
        """
        Based on historical data, estimates how long it will take to get from the back of the queue
        to the front
        """
        if data.get('roomType', None) == 'direct' or (self.message_text == 'how long' and
                                                      self.q.get_member(data['personId'])):
            self.create_message(self._how_long(data['personId']), roomId=data['roomId'])
        else:
            self.create_message(self._how_long(), roomId=data['roomId'])

    def about(self, data):
        """
        Gets information about queuebot
        """
        self.create_message(
            self.about_string,
            roomId=data['roomId']
        )

    def most_active_users(self, data):
        """
        Returns a list of the most active users for this project
        """
        most_active = self.q.get_most_active()
        message = 'Most active user/s for subproject "' + str(self.subproject) + \
                  '" on project ' + str(self.project.get_project()) + ' is:\n\n'
        for person in most_active:
            message += ("- " + person['displayName'] + " (" +
                           str(self.q.get_queue_activity(person['sparkId'])) + " queue activities)") + "\n"
        self.create_message(
            message,
            roomId=data['roomId']
        )

    def largest_queue_depth(self, data):
        """
        Shows the largest queue depth as well as the date at which the queue was that length
        """
        depth, time = self.q.get_largest_queue_depth()
        self.create_message(
            'Largest queue depth for subproject "' + str(self.subproject) +
            '" on project ' + str(self.project.get_project()) + ' is:\n\n**' + str(depth) + '** at ' + str(time),
            roomId=data['roomId']
        )

    def quickest_at_head_user(self, data):
        """
        Returns a list of the user/s that take the least time at the head of the queue
        """
        quickest = self.q.get_quickest_at_head()
        message = 'Quickest at head user/s for subproject "' + str(self.subproject) + \
                  '" on project "' + str(self.project.get_project()) + '" is:\n\n'

        for person in quickest:
            message += ("- " + person['displayName'] + " (" + self._make_time_pretty(
                            self.q.get_median_time_at_queue_head(id=person['sparkId'])
            ) + ")\n")
        self.create_message(
            message,
            roomId=data['roomId']
        )

    def _convert_int_to_time(self, integer):
        return datetime.datetime(year=1, month=1, day=1, hour=integer).strftime('%I%p')

    def get_aggregate_stat_unit(self, data):
        """
        Gets aggregate, max, or min for a given statistic by a given unit. Returns an image of a graph
        """
        function_mapping = {
            ('average', 'queue depth', 'hour'): self.get_average_queue_depth_hour,
            ('max', 'queue depth', 'hour'): self.get_max_queue_depth_hour,
            ('min', 'queue depth', 'hour'): self.get_min_queue_depth_hour,
            ('min', 'flush time', 'hour'): self.get_min_flush_time_hour,
            ('max', 'flush time', 'hour'): self.get_max_flush_time_hour,
            ('average', 'flush time', 'hour'): self.get_average_flush_time_hour,
            ('max', 'queue depth', 'day'): self.get_max_queue_depth_day,
            ('min', 'queue depth', 'day'): self.get_min_queue_depth_day,
            ('average', 'queue depth', 'day'): self.get_average_queue_depth_day,
            ('max', 'flush time', 'day'): self.get_max_flush_time_day,
            ('min', 'flush time', 'day'): self.get_min_flush_time_day,
            ('average', 'flush time', 'day'): self.get_average_flush_time_day,
        }
        aggregate, stat, unit = re.search(
            "show (average|max|min) (queue depth|flush time) by (hour|day)",
            self.message_text
        ).groups()

        function_mapping.get(tuple([aggregate, stat, unit]), self.no_command_found)(data)

    def get_average_flush_time_hour(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: ((sum(x) / len(x)) if x else 0),
            attribute='flushTime',
            unit='hour'
        )

        reformatted = {}
        while len(d):
            k = str(min([int(i) for i in d]))
            reformatted[self._convert_int_to_time(int(k))] = d.pop(k)

        with self._create_bar_graph(
                title="Average Flush Time by Hour for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_average_flush_time_hour_' + str(self.project.get_project()) + '_' + str(self.subproject)+ '.png',
                yaxis_dates=True
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_average_flush_time_day(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: ((sum(x) / len(x)) if x else 0),
            attribute='flushTime',
            unit='day'
        )
        days = {'0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday',
                '4': 'Friday', '5': 'Saturday', '6': 'Sunday'}
        reformatted = {days[str(k)]: d.get(str(k), '0') for k in range(7)}

        with self._create_bar_graph(
                title="Average Flush Time by Day for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_average_flush_time_day_' + str(self.project.get_project()) + '_' + str(self.subproject)+ '.png',
                yaxis_dates=True,
                rotation=0
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_min_queue_depth_hour(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: (min(x) if x else 0),
            attribute='queueDepth',
            unit='hour'
        )

        reformatted = {}
        while len(d):
            k = str(min([int(i) for i in d]))
            reformatted[self._convert_int_to_time(int(k))] = d.pop(k)

        with self._create_bar_graph(
                title="Min Queue Depth by Hour for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_min_queue_depth_hour_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png',
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_max_flush_time_hour(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: (max(x) if x else 0),
            attribute='flushTime',
            unit='hour'
        )

        reformatted = {}
        while len(d):
            k = str(min([int(i) for i in d]))
            reformatted[self._convert_int_to_time(int(k))] = d.pop(k)

        with self._create_bar_graph(
                title="Max Flush Time by Hour for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_max_flush_time_hour_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png',
                yaxis_dates=True
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_max_flush_time_day(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: (max(x) if x else 0),
            attribute='flushTime',
            unit='day'
        )
        days = {'0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday',
                '4': 'Friday', '5': 'Saturday', '6': 'Sunday'}
        reformatted = {days[str(k)]: d.get(str(k), '0') for k in range(7)}

        with self._create_bar_graph(
                title="Max Flush Time by Day for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_max_flush_time_day_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png',
                yaxis_dates=True,
                rotation=0
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_min_flush_time_day(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: (min(x) if x else 0),
            attribute='flushTime',
            unit='day'
        )
        days = {'0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday',
                '4': 'Friday', '5': 'Saturday', '6': 'Sunday'}
        reformatted = {days[str(k)]: d.get(str(k), '0') for k in range(7)}

        with self._create_bar_graph(
                title="Min Flush Time by Day for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_min_flush_time_day_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png',
                yaxis_dates=True,
                rotation=0
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_min_flush_time_hour(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: (min(x) if x else 0),
            attribute='flushTime',
            unit='hour'
        )

        reformatted = {}
        while len(d):
            k = str(min([int(i) for i in d]))
            reformatted[self._convert_int_to_time(int(k))] = d.pop(k)

        with self._create_bar_graph(
                title="Min Flush Time by Hour for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_min_flush_time_hour_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png',
                yaxis_dates=True
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_max_queue_depth_hour(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: (max(x) if x else 0),
            attribute='queueDepth',
            unit='hour'
        )

        reformatted = {}
        while len(d):
            k = str(min([int(i) for i in d]))
            reformatted[self._convert_int_to_time(int(k))] = d.pop(k)

        with self._create_bar_graph(
                title="Max Queue Depth by Hour for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_max_queue_depth_hour_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png'
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_average_queue_depth_hour(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: ((sum(x) / len(x)) if x else 0),
            attribute='queueDepth',
            unit='hour'
        )

        reformatted = {}
        while len(d):
            k = str(min([int(i) for i in d]))
            reformatted[self._convert_int_to_time(int(k))] = d.pop(k)

        with self._create_bar_graph(
                title="Average Queue Depth by Hour for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_average_queue_depth_hour_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png'
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_average_queue_depth_day(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: ((sum(x) / len(x)) if x else 0),
            attribute='queueDepth',
            unit='day'
        )
        days = {'0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday',
                '4': 'Friday', '5': 'Saturday', '6': 'Sunday'}
        reformatted = {days[k]: v for k, v in d.items()}

        with self._create_bar_graph(
                title="Average Queue Depth by Day for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_average_queue_depth_day_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png',
                rotation=0
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_max_queue_depth_day(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: max(x) if x else 0,
            attribute='queueDepth',
            unit='day'
        )
        days = {'0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday',
                '4': 'Friday', '5': 'Saturday', '6': 'Sunday'}
        reformatted = {days[k]: v for k, v in d.items()}

        with self._create_bar_graph(
                title="Max Queue Depth by Day for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_max_queue_depth_day_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png',
                rotation=0
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    def get_min_queue_depth_day(self, data):
        d = self.q.get_function_attribute_by_unit(
            function=lambda x: min(x) if x else 0,
            attribute='queueDepth',
            unit='day'
        )
        days = {'0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday',
                '4': 'Friday', '5': 'Saturday', '6': 'Sunday'}
        reformatted = {days[k]: v for k, v in d.items()}

        with self._create_bar_graph(
                title="Min Queue Depth by Day for '" + str(self.project.get_project()) + "' on subproject '" + str(self.subproject) + "'",
                items=reformatted,
                filename='get_min_queue_depth_day_' + str(self.project.get_project()) + '_' + str(self.subproject) + '.png',
                rotation=0
        ) as file:
            self.api.messages.create(
                files=[file],
                roomId=data['roomId']
            )

    @contextmanager
    def _create_bar_graph(self, title, items, filename, yaxis_dates=False, rotation=45):
        try:
            if yaxis_dates:
                def timeTicks(x, pos):
                    return str(datetime.timedelta(seconds=x))

                formatter = matplotlib.ticker.FuncFormatter(timeTicks)
                pyplot.axes().yaxis.set_major_formatter(formatter)
            pyplot.plot(list(range(len(items))), list(items.values()), '-', color='black')
            pyplot.plot(list(range(len(items))), list(items.values()), 'ro', markersize=4)
            pyplot.grid(True)
            pyplot.title(title)
            pyplot.xticks(range(len(items)), items.keys(), rotation=rotation)
            pyplot.savefig(filename)
            pyplot.gcf().clear()
            yield filename
        finally:
            try:
                os.remove(filename)
            except OSError:
                # File doesn't exist
                pass

    def show_version_number(self, data):
        """
        Shows the current version number
        """
        self.create_message(
            VERSION,
            roomId=data['roomId']
        )

    def show_release_notes(self, data):
        """
        Shows the release notes for all versions of queuebot
        """
        notes = json.load(open(RELEASE_NOTES))
        message = ''
        for version, notes in notes.items():
            message += '\n\n**' + version + '**\n\n' + notes
        self.create_message(
            message,
            roomId=data['roomId']
        )

    def show_release_notes_for(self, data):
        """
        Shows the release notes for the specified version of queuebot
        """
        target = re.search('show release notes for (.*)', self.message_text).group(1)
        raw_notes = json.load(open(RELEASE_NOTES))
        message = ''
        for version, notes in raw_notes.items():
            if version == target:
                message += '\n\n**' + version + '**\n\n' + notes
                break
        else:
            message = '"' + str(target) + '" is not a valid release. Please use one of:\n\n- ' + '\n- '.join(raw_notes.keys())
        self.create_message(
            message,
            roomId=data['roomId']
        )
