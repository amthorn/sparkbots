import atexit
import datetime
import json
import os

from apscheduler.scheduler import Scheduler
from config import PROJECT_CONFIG, QUEUE_BOT, DEV_QUEUE_BOT, PRODUCTION, WARNINGS_FILE
from queuebot.projects import ProjectManager
from ciscosparkapi import CiscoSparkAPI
from dateutil import parser
from app import PROJECT_STALE_SECONDS_FIRST, PROJECT_STALE_SECONDS_SECOND, PROJECT_STALE_SECONDS, \
    PROJECT_STALE_SECONDS_FINAL

cron = Scheduler(daemon=True)

# Explicitly kick off the background thread
if PRODUCTION:
    cron.start()

@cron.interval_schedule(minutes=1, misfire_grace_time=5)
def job_function():
    try:
        if PRODUCTION:
            token = QUEUE_BOT
        else:
            token = DEV_QUEUE_BOT

        # Read projects in
        api = CiscoSparkAPI(token)
        project_manager = ProjectManager(api, roomId=None)
        all_projects = project_manager.get_projects()

        for project in all_projects:
            file = WARNINGS_FILE.format(project)

            if not os.path.exists(file):
                warnings = {'first': False, 'second': False, 'third': False, 'final': False}
                json.dump(warnings, open(file, 'w'))
            else:
                warnings = json.load(open(file))

            all_commands = project_manager.get_commands(project)
            last_command = max([parser.parse(i['timeIssued']) for i in all_commands])
            if (datetime.datetime.now() - last_command).total_seconds() < PROJECT_STALE_SECONDS_FIRST:
                # Command was run, reset warnings.
                warnings = {'first': False, 'second': False, 'third': False, 'final': False}
                json.dump(warnings, open(file, 'w'))
            if (datetime.datetime.now() - last_command).total_seconds() > PROJECT_STALE_SECONDS:
                # Project is stale, marking for deletion
                # project_manager.delete_project()
                if not warnings['final']:
                    all_rooms = set(project_manager.get_rooms(project))
                    for room in all_rooms:
                        try:
                            api.messages.create(
                                markdown='Project "' + str(project) + '" hasn\'t been used in 3 weeks. '
                                                                      'It is stale and has been marked for deletion',
                                roomId=room
                            )
                        except Exception as e:
                            # If it doesn't sent to a room, room was likely deleted. Ignore
                            print(e)
                    warnings['final'] = True
                    json.dump(warnings, open(file, 'w'))
            elif (datetime.datetime.now() - last_command).total_seconds() > PROJECT_STALE_SECONDS_FINAL:
                # Final warning
                if not warnings['third']:
                    all_rooms = set(project_manager.get_rooms(project))
                    for room in all_rooms:
                        try:
                            api.messages.create(
                                markdown='Project "' + str(project) + '" hasn\'t been used in 3 weeks. '
                                                                      'If the project is unused for 1 more day, '
                                                                      'it will be marked for deletion',
                                roomId=room
                            )
                        except Exception as e:
                            # If it doesn't sent to a room, room was likely deleted. Ignore
                            print(e)
                    warnings['third'] = True
                    json.dump(warnings, open(file, 'w'))
            elif (datetime.datetime.now() - last_command).total_seconds() > PROJECT_STALE_SECONDS_SECOND:
                # Check if project was already warned for second warning
                if not warnings['second']:
                    all_rooms = set(project_manager.get_rooms(project))
                    for room in all_rooms:
                        try:
                            api.messages.create(
                                markdown='Project "' + str(project) + '" hasn\'t been used for 2 weeks. '
                                                                      'If the project is unused for 1 more week, '
                                                                      'it will be marked for deletion.',
                                roomId=room
                            )
                        except Exception as e:
                            # If it doesn't sent to a room, room was likely deleted. Ignore
                            print(e)
                    warnings['second'] = True
                    json.dump(warnings, open(file, 'w'))
            elif (datetime.datetime.now() - last_command).total_seconds() > PROJECT_STALE_SECONDS_FIRST:
                # Check if project was already warned for first warning
                if not warnings['first']:
                    all_rooms = set(project_manager.get_rooms(project))
                    for room in all_rooms:
                        try:
                            api.messages.create(
                                markdown='Project "' + str(project) + '" hasn\'t been used for a week. '
                                                                      'If the project is unused for 2 more weeks, '
                                                                      'it will be marked for deletion.',
                                roomId=room
                            )
                        except Exception as e:
                            # If it doesn't sent to a room, room was likely deleted. Ignore
                            print(e)
                    warnings['first'] = True
                    json.dump(warnings, open(file, 'w'))
    except Exception as e:
        if not PRODUCTION:
            raise
        print(e)
# Shutdown your cron thread if the web process is stopped
atexit.register(lambda: cron.shutdown(wait=False))