import datetime
import os
import json
import re
import requests
import csv
import numpy
import matplotlib
matplotlib.use('Agg')

from dateutil import parser
from matplotlib import pyplot
from queuebot.queue import Queue
from queuebot.people import PeopleManager
from queuebot.commands import CommandManager
from queuebot.admins import AdminManager
from app import app, logger, FORMAT_STRING, TIMEOUT, CSV_FILE_FORMAT, VERSION, RELEASED, AUTHOR, EMAIL, QUEUE_THRESHOLD, RELEASE_NOTES
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
            'about': self.about,
            'show version': self.show_version_number,
            'show release notes': self.show_release_notes,
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
            'show all stats as csv': self.get_stats_csv,
            'show all stats': self.get_stats,
            'show stats for (.*)': self.get_stats_for,
            'add person (.*)': self.add_person,
            'remove person (.*)': self.remove_person,
            'show most active users': self.most_active_users,
            'show largest queue depth': self.largest_queue_depth,
            'show quickest users': self.quickest_at_head_user,
            'show (average|max|min) (queue depth|flush time) by (hour|day)': self.get_aggregate_stat_unit,
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

        command_strings = ''

        for command, docstring in self._commands_with_help_string().items():
            docstring = self._clean_docstring(docstring)
            command_strings += '- **' + command + (('** (' + docstring + ')\n') if docstring else '**\n')

        self.help_string = \
            "This bot is to be used to manage a queue for a given team. " \
            "It can be used to get statistical information as well as manage an individual queue.\n\n" \
            "This QueueBot is registered to '" + str(self.project) + "'\n\n" \
            "Available commands are:\n\n" + command_strings + \
            "\nFor admins, use 'show admin commands' to see a list of admin commands"

        self.about_string = \
            "This bot is to be used to manage a queue for a given team. " \
            "It can be used to get statistical information as well as manage an individual queue.\n" \
            "\n" \
            "This QueueBot is registered to '" + str(self.project) + "'\n" \
            "\n" \
            "Version: **" + str(VERSION) + "**\n\n" \
            "Released: " + str(RELEASED) + "\n\n" \
            "Author: " + str(AUTHOR) + " (" + str(EMAIL) + ")"

    def _clean_docstring(self, docstring):
        if docstring:
            docstring = docstring.strip('\n ')
            while '  ' in docstring:
                docstring = re.sub('  ', ' ', docstring)
            docstring = docstring.replace('\n', '')
            return docstring

    def _commands_with_help_string(self):
        return {k: v.__doc__ for k, v in sorted(self.supported_commands.items())}

    def _admin_commands_with_help_string(self):
        return {k: v.__doc__ for k, v in sorted(self.supported_admin_commands.items())}

    def status(self, data):
        """
        Shows the current status of queuebot
        """
        message = "STATUS: OK"

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
                self._create_markdown_table(self._get_stats(stat.upper())),
                roomId=data['roomId']
            )

    def get_stats(self, data):
        """
        Returns a markdown table of global statistics for the project
        """
        self.create_message(
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
                                    round((datetime.datetime.now() - time_enqueued).total_seconds())) + ' seconds')
                else:
                    stats[target or 'TOTAL TIME IN QUEUE'].append(str(person['totalTimeInQueue']) + ' seconds')
            if not target or target == 'TOTAL TIME AT QUEUE HEAD':
                if len(queue) and queue[0]['personId'] == person['sparkId']:
                    time_enqueued = parser.parse(queue[0]['atHeadTime'])
                    stats[target or 'TOTAL TIME AT QUEUE HEAD'].append(str(person['totalTimeAtHead'] +
                                         round((datetime.datetime.now() - time_enqueued).total_seconds())) + ' seconds')
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
                    "Please use one of:\n- " + str('\n- '.join(sorted(self.supported_commands))),
                    data['roomId']
                )
            else:
                self.arg_exists(self.message_text)(data)

    def add_me(self, data):
        """
        Adds you to the back of the queue
        """
        logger.debug("Executing add me")
        person = self.q.add_to_queue(data, self.project)
        if not person:
            self.create_message(
                'Failed to add to queue because queue is already at maximum of "' + str(QUEUE_THRESHOLD) + '"',
                roomId=data['roomId']
            )
        else:
            self.create_message("Adding '"+ str(person.displayName) + "'", data['roomId'])
            self.list_queue(data)

    def list_queue(self, data):
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

        self.create_message(
            'Current queue is:\n\n' + people + '\n\n' + self._how_long(),
            data['roomId']
        )

    def remove_me(self, data):
        """
        Removes the first occurence of you from the queue
        """
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
        """
        Shows all the admins for the current project
        """
        admin_names = [self.api.people.get(i).displayName for i in (self.admins.get_admins() + GLOBAL_ADMINS)]
        admins_nice = '- '.join([(i + '\n') for i in admin_names])
        self.create_message(
            "Admins for '" + str(self.project) + "' are:\n- " + admins_nice,
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
        But one room cannot be registered to multiple bots
        """
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
        """
        Shows the project that the current room is registered to
        """
        self.create_message(
            "QueueBot registration: " + str(self.project),
            data['roomId']
        )

    def show_command_history(self, data):
        """
        Shows the last X commands that were issued on this project where X is a non-negative integer
        """
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
            person = self.q.add_to_queue(person_data, self.project)
            if not person:
                self.create_message(
                    'Failed to add to queue because queue is already at maximum of "' + str(QUEUE_THRESHOLD) + '"',
                    roomId=data['roomId']
                )
            else:
                self.create_message("Adding '"+ str(person.displayName) + "'", data['roomId'])
                self.list_queue(data)

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
            self.create_message("Removing '"+ str(person.displayName) + "'", data['roomId'])
            if not self.q.remove_from_queue(person_data):
                self.create_message("ERROR: '" + str(person.displayName) + "' was not found in the queue", data['roomId'])
            else:
                self.list_queue(data)

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
        display = "All people that have used this bot for project '" + str(self.project) + "' are:\n"
        if people_on_project:
            for index, person in enumerate(people_on_project):
                display += str(index + 1) + ". " + person['displayName'] + '\n'
        else:
            # This line is likely unreachable.
            display += 'There are no people that have used this bot on this project'

        self.create_message(display, roomId=data['roomId'])

    def get_stats_csv(self, data):
        """
        Returns a CSV file attachment containing global statistics for the project
        """
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

    def _how_long(self):
        seconds = 0
        flush_time = self.q.get_estimated_flush_time()

        return 'Given that there are ' + str(len(self.q.get_queue())) + ' people in the queue. ' \
                                                          'Estimated wait time from the back of the queue is:\n\n' + \
               str(self._make_time_pretty(flush_time))

    def how_long(self, data):
        """
        Based on historical data, estimates how long it will take to get from the back of the queue
        to the front
        """
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
        message = 'Most active user/s for project ' + str(self.project) + ' is:\n\n'
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
            'Largest queue depth for ' + str(self.project) + ' is **' + str(depth) + '** at ' + str(time),
            roomId=data['roomId']
        )

    def quickest_at_head_user(self, data):
        """
        Returns a list of the user/s that take the least time at the head of the queue
        """
        quickest = self.q.get_quickest_at_head()
        message = 'Quickest at head user/s for project ' + str(self.project) + ' is:\n\n'

        for person in quickest:
            message += ("- " + person['displayName'] + " (" + self._make_time_pretty(
                            self.q.get_average_time_at_queue_head(person['sparkId'])
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
        }
        aggregate, stat, unit = re.search(
            "show (average|max|min) (queue depth|flush time) by (hour|day)",
            self.message_text
        ).groups()

        function_mapping.get(tuple([aggregate, stat, unit]), lambda data: None)(data)

    def get_average_flush_time_hour(self, data):
        self.q._update_save_global_stats()
        filename = 'get_average_flush_time_hour_' + str(self.project) + '.png'
        d = self.q.get_average_flush_time_by_hour()

        reformatted = {}
        for k, v in d.items():
            reformatted[self._convert_int_to_time(int(k))] = v

        pyplot.bar(range(len(reformatted)), reformatted.values(), align='center')
        pyplot.title("Average Flush Time by Hour for '" + str(self.project) + "'")

        def timeTicks(x, pos):
            return str(datetime.timedelta(seconds=x))

        formatter = matplotlib.ticker.FuncFormatter(timeTicks)
        pyplot.axes().yaxis.set_major_formatter(formatter)

        pyplot.xticks(range(len(reformatted)), reformatted.keys(), rotation=45)
        pyplot.savefig(filename)
        pyplot.gcf().clear()

        self.api.messages.create(
            files=[filename],
            roomId=data['roomId']
        )
        os.remove(filename)

    def get_min_queue_depth_hour(self, data):
        filename = 'get_min_queue_depth_hour_' + str(self.project) + '.png'
        d = self.q.get_min_queue_depth_by_hour()

        reformatted = {}
        for k, v in d.items():
            reformatted[self._convert_int_to_time(int(k))] = v

        pyplot.bar(range(len(reformatted)), reformatted.values(), align='center')
        pyplot.title("Min Queue Depth by Hour for '" + str(self.project) + "'")
        pyplot.xticks(range(len(reformatted)), reformatted.keys(), rotation=45)
        pyplot.savefig(filename)
        pyplot.gcf().clear()

        self.api.messages.create(
            files=[filename],
            roomId=data['roomId']
        )
        os.remove(filename)

    def get_max_flush_time_hour(self, data):
        filename = 'get_max_flush_time_hour_' + str(self.project) + '.png'
        d = self.q.get_max_flush_time_by_hour()

        reformatted = {}
        for k, v in d.items():
            reformatted[self._convert_int_to_time(int(k))] = v

        pyplot.bar(range(len(reformatted)), reformatted.values(), align='center')
        pyplot.title("Max Flush Time by Hour for '" + str(self.project) + "'")

        def timeTicks(x, pos):
            return str(datetime.timedelta(seconds=x))

        formatter = matplotlib.ticker.FuncFormatter(timeTicks)
        pyplot.axes().yaxis.set_major_formatter(formatter)

        pyplot.xticks(range(len(reformatted)), reformatted.keys(), rotation=45)
        pyplot.savefig(filename)
        pyplot.gcf().clear()

        self.api.messages.create(
            files=[filename],
            roomId=data['roomId']
        )
        os.remove(filename)

    def get_min_flush_time_hour(self, data):
        filename = 'get_min_flush_time_hour_' + str(self.project) + '.png'
        d = self.q.get_min_flush_time_by_hour()

        reformatted = {}
        for k, v in d.items():
            reformatted[self._convert_int_to_time(int(k))] = v

        pyplot.bar(range(len(reformatted)), reformatted.values(), align='center')
        pyplot.title("Min Flush Time by Hour for '" + str(self.project) + "'")

        def timeTicks(x, pos):
            return str(datetime.timedelta(seconds=x))

        formatter = matplotlib.ticker.FuncFormatter(timeTicks)
        pyplot.axes().yaxis.set_major_formatter(formatter)

        pyplot.xticks(range(len(reformatted)), reformatted.keys(), rotation=45)
        pyplot.savefig(filename)
        pyplot.gcf().clear()

        self.api.messages.create(
            files=[filename],
            roomId=data['roomId']
        )
        os.remove(filename)

    def get_max_queue_depth_hour(self, data):
        filename = 'get_max_queue_depth_hour_' + str(self.project) + '.png'
        d = self.q.get_max_queue_depth_by_hour()

        reformatted = {}
        for k, v in d.items():
            reformatted[self._convert_int_to_time(int(k))] = v

        pyplot.bar(range(len(reformatted)), reformatted.values(), align='center')
        pyplot.title("Max Queue Depth by Hour for '" + str(self.project) + "'")
        pyplot.xticks(range(len(reformatted)), reformatted.keys(), rotation=45)
        pyplot.savefig(filename)
        pyplot.gcf().clear()

        self.api.messages.create(
            files=[filename],
            roomId=data['roomId']
        )
        os.remove(filename)


    def get_average_queue_depth_hour(self, data):
        filename = 'get_average_queue_depth_hour_' + str(self.project) + '.png'
        d = self.q.get_average_queue_depth_by_hour()

        reformatted = {}
        for k, v in d.items():
            reformatted[self._convert_int_to_time(int(k))] = v

        pyplot.bar(range(len(reformatted)), reformatted.values(), align='center')
        pyplot.title("Average Queue Depth by Hour for '" + str(self.project) + "'")
        pyplot.xticks(range(len(reformatted)), reformatted.keys(), rotation=45)
        pyplot.savefig(filename)
        pyplot.gcf().clear()

        self.api.messages.create(
            files=[filename],
            roomId=data['roomId']
        )
        os.remove(filename)

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
            message += '**' + version + '**\n\n' + notes
        self.create_message(
            message,
            roomId=data['roomId']
        )
