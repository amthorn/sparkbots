import glob
import json
import re
import os

from collections import defaultdict

pickle_files = glob.glob("*.pickle")

FOR_REAL = True

for file in pickle_files:
    if file == 'admins.pickle':
        for project, admins in json.load(open(file)).items():
            if FOR_REAL:
                os.makedirs('queuebot/data/' + str(project), exist_ok=True)
                json.dump(admins, open('queuebot/data/' + str(project) + '/admins.pickle', 'w'), indent=4, separators=(',', ': '))
    elif file == 'commands.pickle':
        commands = defaultdict(list)
        for command in json.load(open(file)):
            cleaned = {k: v for k, v in command.items() if k != 'project'}
            commands[command['project']].append(cleaned)

        for project, commands in commands.items():
            if FOR_REAL:
                os.makedirs('queuebot/data/' + str(project), exist_ok=True)
                json.dump(commands, open('queuebot/data/' + str(project) + '/commands.pickle', 'w'), indent=4, separators=(',', ': '))

    elif file == 'people.pickle':
        people = defaultdict(list)
        for person in json.load(open(file)):
            cleaned = {
                k: v
                for k, v in person.items()
                if k != 'project'
            }
            cleaned['added_to_queue'] = cleaned.get('added_to_queue', [])
            cleaned['removed_from_queue'] = cleaned.get('removed_from_queue', [])
            people[person['project']].append(cleaned)

        for project, project_people in people.items():
            if FOR_REAL:
                os.makedirs('queuebot/data/' + str(project), exist_ok=True)
                json.dump(project_people, open('queuebot/data/' + str(project) + '/people.pickle', 'w'), indent=4, separators=(',', ': '))
    elif file == 'projects.pickle':
        if FOR_REAL:
            os.makedirs('queuebot/data/' + str(project), exist_ok=True)
            json.dump(json.load(open(file)), open('queuebot/data/projects.pickle', 'w'), indent=4, separators=(',', ': '))
    else:
        project = re.search("(.*?)\-queue.pickle", file).group(1)
        if FOR_REAL:
            os.makedirs('queuebot/data/' + str(project), exist_ok=True)
            json.dump(json.load(open(file)), open('queuebot/data/' + str(project) + '/queue.pickle', 'w'),
                      indent=4, separators=(',', ': '))