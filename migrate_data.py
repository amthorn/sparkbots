import glob
import json
import re
import os
import time

from collections import defaultdict
from config import DATA_FOLDER

# pickle_files = glob.glob("queuebot/data/")

FOR_REAL = True

proj_conf_file = 'queuebot/data/projects.pickle'
new_project_config = []

for room, project in json.load(open(proj_conf_file)).items():
    if FOR_REAL and os.path.exists(DATA_FOLDER.format(project)):
        print(str(project) + ' -- ' + str(room))
        new_project_config.append(tuple([project, room]))

if FOR_REAL:
    json.dump(new_project_config, open(proj_conf_file, 'w'))

for project in os.listdir('queuebot/data'):
    if project != 'projects.pickle':
        print(project)
        if FOR_REAL:
            os.makedirs('queuebot/data/' + str(project) + '/GENERAL')
            if os.path.exists('queuebot/data/' + str(project) + '/queue.pickle'):
                os.rename('queuebot/data/' + str(project) + '/queue.pickle', 'queuebot/data/' + str(project) + '/GENERAL/queue.pickle')
            if os.path.exists('queuebot/data/' + str(project) + '/global-stats.pickle'):
                os.rename('queuebot/data/' + str(project) + '/global-stats.pickle', 'queuebot/data/' + str(project) + '/GENERAL/global-stats.pickle')
                global_stats = json.load(open('queuebot/data/' + str(project) + '/GENERAL/global-stats.pickle'))
                global_stats['maxQueueDepthByDay'] = {}
                global_stats['minQueueDepthByDay'] = {}
                global_stats['maxFlushTimeByDay'] = {}
                global_stats['minFlushTimeByDay'] = {}
                json.dump(global_stats, open('queuebot/data/' + str(project) + '/GENERAL/global-stats.pickle', 'w'))
            if os.path.exists('queuebot/data/' + str(project) + '/people.pickle'):
                os.rename('queuebot/data/' + str(project) + '/people.pickle', 'queuebot/data/' + str(project) + '/GENERAL/people.pickle')
            if os.path.exists('queuebot/data/' + str(project) + '/commands.pickle'):
                os.rename('queuebot/data/' + str(project) + '/commands.pickle', 'queuebot/data/' + str(project) + '/GENERAL/commands.pickle')
            json.dump({
                'default_subproject': 'GENERAL',
                'strict_regex': True
            }, open('queuebot/data/' + str(project) + '/settings.json', 'w'))
