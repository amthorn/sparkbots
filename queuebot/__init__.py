import datetime
import os
import json
import re
import requests
import csv

from dateutil import parser
from queuebot.queue import Queue
from queuebot.people import PeopleManager
from queuebot.commands import CommandManager
from queuebot.admins import AdminManager
from app import app, logger, FORMAT_STRING, TIMEOUT, CSV_FILE_FORMAT, VERSION, RELEASED, AUTHOR, EMAIL
from config import PROJECT_CONFIG, GLOBAL_ADMINS


class Bot():
    def __init__(self, api, data):
        self.api = api
        self.project = self.get_registered_project(data['roomId'])

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
            'help': self.help,
            'status': self.status,
            'how long': self.how_long,
            'about': self.about
        }
        logger.debug('supported commands:\n' + str(self.supported_commands.keys()))

        self.supported_admin_commands = {
            'show admin commands': self.show_admin_commands,
            'show admins': self.show_admins,
            'add admin (\w+)': self.add_admin,
            'remove admin (\w+)': self.remove_admin,
            'register bot to project .*': self.register_bot,
            'show registration': self.show_registration,
            'show last (\d*) commands': self.show_command_history,
            'show people': self.show_people,
            'get all stats as csv': self.get_stats_csv,
            'get all stats': self.get_stats,
            'get stats for (.*)': self.get_stats_for,
            'add person (.*)': self.add_person,
            'remove person (.*)': self.remove_person
        }
        logger.debug('supported admin commands:\n' + str(self.supported_admin_commands.keys()))

        logger.debug("Initializing People Manager")
        self.people = PeopleManager(self.api, project=self.project)
        logger.debug("Initialized People Manager")

        logger.debug("Initializing Admin Manager")
        self.admins = AdminManager(self.api, project=self.project, people_manager=self.people)
        logger.debug("Initialized Admin Manager")

        logger.debug("Initializing Queue")
        self.q = Queue(self.api, project=self.project, people_manager=self.people)
        logger.debug("Initialized Queue")

        logger.debug("Initializing Command Manager")
        self.commands = CommandManager(self.api, project=self.project, people_manager=self.people)
        logger.debug("Initialized Command Manager")

        logger.debug("Getting Admins for '" + str(self.project) + "'")

        if not os.path.exists(PROJECT_CONFIG):
            json.dump({}, open(PROJECT_CONFIG, 'w'))

        logger.debug("Admins for '" + str(self.project) + "' are:\n" + str(self.admins))

        self.help_string = \
            "This bot is to be used to manage a queue for a given team. " \
            "It can be used to get statistical information as well as manage an individual queue.\n" \
            "\n" \
            "This QueueBot is registered to '" + str(self.project) + "'\n" \
            "\n" \
            "Available commands are:\n- " \
            + '- '.join([(i + '\n') for i in self.supported_commands]) + \
            "\n" \
            "For admins, use 'show admin commands' to see a list of admin commands"

        self.about_string = \
            "This bot is to be used to manage a queue for a given team. " \
            "It can be used to get statistical information as well as manage an individual queue.\n" \
            "\n" \
            "This QueueBot is registered to '" + str(self.project) + "'\n" \
            "\n" \
            "Version: **" + str(VERSION) + "**\n\n" \
            "Released: " + str(RELEASED) + "\n\n" \
            "Author: " + str(AUTHOR) + " (" + str(EMAIL) + ")"

    def status(self, data):
        message = "STATUS: OK"

        self.create_message(
            message,
            roomId=data['roomId']
        )

    def get_stats_for(self, data):
        stat = re.search('get stats for (.*)', self.message_text).group(1)
        if stat.upper() not in self.column_names:
            self.create_message(
                "Column '" + str(stat) + "' is not a valid column. Try one of: " + ', '.join(self.column_names),
                roomId=data['roomId']
            )
        else:
            self.create_message(
                self._create_markdown_table(self._get_stats(stat.upper())),
                roomId=data['roomId']
            )

    def get_stats(self, data):
        self.create_message(
            self._create_markdown_table(self._get_stats()),
            roomId=data['roomId']
        )

    # def _get_stats_by(self, column):
    #     column_widths = self.column_widths
    #
    #     if column == 'PERSON':
    #         return 'Cannot get data for "PERSON" column'
    #     elif column.UPPER() not in column_widths:
    #         return 'Column "' + str(column) + '" does not exist'
    #
    #
    #     for person in people:
    #         if len(str(person['displayName'])) > len(column_widths['PERSON'] * ' '):
    #             column_widths['PERSON'] = (len(str(person['displayName']))) + 1
    #
    #         if len(str(person['commands'])) > len(column_widths['COMMANDS ISSUED'] * ' '):
    #             column_widths['COMMANDS ISSUED'] = (len(str(person['commands']))) + 1

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

        for index, column in enumerate(dictionary):
            message += column.center(widths[column], ' ') + (" | " if index < len(dictionary) - 1 else '\n')

        for index in range(column_length):
            for column_index, column in enumerate(dictionary):
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
                    stats[target or 'TOTAL TIME IN QUEUE'].append(str(person['totalTimeInQueue'] + \
                                    (datetime.datetime.now() - time_enqueued).seconds) + ' seconds')
                else:
                    stats[target or 'TOTAL TIME IN QUEUE'].append(str(person['totalTimeInQueue']) + ' seconds')
            if not target or target == 'TOTAL TIME AT QUEUE HEAD':
                if len(queue) and queue[0]['personId'] == person['sparkId']:
                    time_enqueued = parser.parse(queue[0]['atHeadTime'])
                    stats[target or 'TOTAL TIME AT QUEUE HEAD'].append(str(person['totalTimeAtHead'] +
                                         (datetime.datetime.now() - time_enqueued).seconds) + ' seconds')
                else:
                    stats[target or 'TOTAL TIME AT QUEUE HEAD'].append(str(person['totalTimeAtHead']) + ' seconds')

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
                stats[target or 'NUMBER OF TIMES IN QUEUE'].append(str(person['number_of_times_in_queue']))
        return stats

    def get_registered_project(self, roomId):
        if not os.path.exists(PROJECT_CONFIG):
            return None
        else:
            return json.load(open(PROJECT_CONFIG, 'r')).get(roomId, None)

    def create_message(self, message, roomId):
        logger.debug("Sending Message '" + message + "' to room '" + roomId + "' ")
        self.api.messages.create(markdown=message, roomId=roomId)
        logger.debug("Message Sent")

    def arg_exists(self, string):
        for command in self.supported_commands:
            if re.search(command, string.lower()):
                logger.debug("Found function for command '" + str(string) + "'")
                return self.supported_commands[command]
        else:
            logger.debug("No function found for command '" + str(string) + "'")
            return None

    def admin_arg_exists(self, string):
        for command in self.supported_admin_commands:
            if re.search(command, string.lower()):
                logger.debug("Found admin function for command '" + str(string) + "'")
                return self.supported_admin_commands[command]
        else:
            logger.debug("No admin function found for command '" + str(string) + "'")
            return None

    def handle_data(self, data):
        person = self.people.add_person(data)
        self.message_text, self.message = self.commands.add_command(data, person, self.project)

        if self.message_text.lower() == 'help':
            self.supported_commands['help'](data)
        elif self.message_text.lower() == 'cat fact':
            self.create_message(
                requests.get('https://catfact.ninja/fact').json()['fact'],
                roomId=data['roomId']
            )
        elif self.message_text.lower() == 'pun':
            self.create_message(
                requests.get('https://icanhazdadjoke.com/', headers={'Accept': 'application/json'}).json()['joke'],
                roomId=data['roomId']
            )
        elif self.admin_arg_exists(self.message_text):
            if self.admins.is_admin(id=data['personId']):
                self.admin_arg_exists(self.message_text)(data)
            else:
                self.create_message(
                    'You are not registered as an admin.',
                    roomId=data['roomId']
                )
        else:
            if not self.project:
                message = "QueueBot is not registered to a project! Ask an admin to register this bot"
                self.create_message(message, data['roomId'])
            elif not self.arg_exists(self.message_text):
                self.create_message(
                    "Unrecognized Command: '" + self.message_text.lower() + "'\n\n" +
                    "Please use one of:\n- " + str('\n- '.join(self.supported_commands)),
                    data['roomId']
                )
            else:
                self.arg_exists(self.message_text)(data)

    def add_me(self, data):
        logger.debug("Executing add me")
        person = self.q.add_to_queue(data, self.project)
        self.create_message("Adding '"+ str(person.displayName) + "'", data['roomId'])
        self.list_queue(data)

    def list_queue(self, data):
        logger.debug("Executing list queue")
        queue = self.q.get_queue()

        if queue:
            people = ''
            for index, member in enumerate(queue):
                people += str(index + 1) + '. ' + self.format_person(member) + '\n'
        else:
            people = 'There is no one in the queue'

        self.create_message(
            'Current queue is:\n\n' + people,
            data['roomId']
        )

    def remove_me(self, data):
        logger.debug("Executing remove me")
        person = self.api.people.get(data['personId'])
        self.create_message("Removing '"+ str(person.displayName) + "'", data['roomId'])
        if not self.q.remove_from_queue(data):
            self.create_message("ERROR: '" + str(person.displayName) + "' was not found in the queue", data['roomId'])
        else:
            self.list_queue(data)

    def format_person(self, person):
        formatted_date = parser.parse(person['timeEnqueued'])
        return person['displayName'] + " (" + formatted_date.strftime(FORMAT_STRING) + ")"

    def show_admins(self, data):
        admin_names = [self.api.people.get(i).displayName for i in (self.admins.get_admins() + GLOBAL_ADMINS)]
        admins_nice = '- '.join([(i + '\n') for i in admin_names])
        self.create_message(
            "Admins for '" + str(self.project) + "' are:\n- " + admins_nice,
            roomId=data['roomId']
        )

    def help(self, data):
        self.create_message(
            self.help_string,
            data['roomId']
        )

    def show_admin_commands(self, data):
        self.create_message(
            'Available admin commands are:\n- ' + ('- '.join([(i + '\n') for i in self.supported_admin_commands])),
            roomId=data['roomId']
        )

    def register_bot(self, data):
        project = re.search('register bot to project (.*)', self.message_text).group(1)
        registrations = json.load(open(PROJECT_CONFIG, 'r'))
        self.project = project.upper()
        registrations[data['roomId']] = self.project
        json.dump(registrations, open(PROJECT_CONFIG, 'w'))
        self.create_message(
            "Registered bot to project '" + str(self.project) + "'",
            roomId=data['roomId']
        )
        self.header_string = "QueueBot: '" + str(self.project) + "'"
        return registrations

    def show_registration(self, data):
        self.create_message(
            "QueueBot registration: " + str(self.project),
            data['roomId']
        )

    def show_command_history(self, data):
        number = int(re.search('show last (\d*) commands', self.message_text).group(1))
        commands = self.commands.get_commands(project=self.project)
        command_string = ''
        for index, command in enumerate(commands[::-1]):
            if index >= number:
                break
            time = parser.parse(command['timeIssued'])
            command_string += str(index + 1) + '. ' + command['command'] + ' (' + str(command['displayName']) + \
                              ' executed at ' + str(time.strftime(FORMAT_STRING)) + ')\n'

        self.create_message(
            "Last " + str(number) + " commands are:\n" + command_string,
            roomId=data['roomId']
        )

    def add_person(self, data):
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
            person = self.q.add_to_queue(person_data, self.project)
            self.create_message("Adding '"+ str(person.displayName) + "'", data['roomId'])
            self.list_queue(data)

    def remove_person(self, data):
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
            self.create_message("Removing '"+ str(person.displayName) + "'", data['roomId'])
            if not self.q.remove_from_queue(person_data):
                self.create_message("ERROR: '" + str(person.displayName) + "' was not found in the queue", data['roomId'])
            else:
                self.list_queue(data)

    def add_admin(self, data):
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
        people_on_project = self.people.get_people()
        display = "All people that have used this bot for project '" + str(self.project) + "' are:\n"
        if people_on_project:
            for index, person in enumerate(people_on_project):
                display += str(index + 1) + ". " + person['displayName'] + '\n'
        else:
            # This line is likely unreachable.
            display += 'There are no people that have used this bot on this project'

        self.create_message(display, roomId=data['roomId'])

    def get_stats_csv(self, data):
        stats = self._get_stats()
        rows = [list(stats.keys())] + [list(i) for i in zip(*stats.values())]
        with open(CSV_FILE_FORMAT.format(self.project), 'w') as csvfile:
            spamwriter = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            for row in rows:
                spamwriter.writerow(row)
        self.api.messages.create(
            markdown="Here are all the stats for project '" + str(self.project) + "' as a csv",
            files=[CSV_FILE_FORMAT.format(self.project)],
            roomId=data['roomId']
        )
        os.remove(CSV_FILE_FORMAT.format(self.project))

    def _make_time_pretty(self, seconds):
        return str(datetime.timedelta(seconds=seconds))

    def how_long(self, data):
        """
        Based on historical data, estimates how long it will take to get from the back of the queue
        to the front
        :param data:
        :return:
        """
        seconds = 0
        index = -1

        for index, member in enumerate(self.q.get_queue()):
            seconds += self.q.get_average_time_at_queue_head(member['personId'])

        self.create_message(
            'Given that there are ' + str(index + 1) + ' people in the queue. '
                                                   'Estimated wait time from the back of the queue is:\n\n' +
            str(self._make_time_pretty(seconds)),
            roomId=data['roomId']
        )

    def about(self, data):
        self.create_message(
            self.about_string,
            roomId=data['roomId']
        )