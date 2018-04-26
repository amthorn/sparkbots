import ciscosparkapi
import flask
import re
import matplotlib
matplotlib.use('Agg')
import json

from functools import wraps, partial
from unittest import mock
from attrdict import AttrDict
from config import PROJECT_CONFIG, QUEUE_FILE, PEOPLE_FILE, GLOBAL_STATS_FILE, COMMANDS_FILE, ADMINS_FILE, SETTINGS_FILE, DATA_FOLDER
from app import RELEASE_NOTES
import config

r_notes = json.load(open(RELEASE_NOTES))
ME_ID = 'me_id'

def with_request(
        data,
        project=[],
        subprojects=['GENERAL'],
        queue=[],
        global_stats={},
        people=[],
        commands=[],
        admins=[],
        mock_people={},
        settings={
            'default_subproject': 'GENERAL',
            'strict_regex': True
        },
        random=1
):
    def load_side_effect(*args, **kwargs):
        file_name = open.call_args_list[-1][0][0]
        files = {
            PROJECT_CONFIG: project,
            QUEUE_FILE: queue,
            GLOBAL_STATS_FILE: global_stats,
            PEOPLE_FILE: people,
            COMMANDS_FILE: commands,
            ADMINS_FILE: admins,
            RELEASE_NOTES: r_notes,
            SETTINGS_FILE: settings
        }
        return files.get([i for i in files if re.search(i.format(*[".*?"] * i.count("{}")), file_name)][0])

    def api_get_side_effect(*args, **kwargs):
        return mock_people.get(args[0], AttrDict({
                     'displayName': 'Unit Test Display Name',
                     'lastName': 'Unit Test Last Name',
                     'emails': ['unitTestEmails@unit.test'],
                     'avatar': 'Unit Test Avatar',
                     'id': ME_ID
                 }))

    def mock_os_walk_side_effect(path, *args, **kwargs):
        if path.endswith('sparkbots/queuebot/data'):
            # Getting projects
            return [[
                path, # PATH
                # FOLDERS
                list(set(i[0] for i in project)),
                # FILES
                [
                    '__init__.py',
                    'admins.py',
                    'commands.py',
                    'decorators.py',
                    'people.py',
                    'projects.py',
                    'queue.py',
                    'rejection_pic.jpg'
                ]
            ]]
        elif len(re.search(DATA_FOLDER.format(*["(.*)"] * DATA_FOLDER.count("{}")), path).groups()) == 1:
            return [[
                path,
                # FOLDERS
                subprojects,
                # FILES
                [
                    'commands.pickle',
                    'global-stats.pickle',
                    'queue.pickle',
                    'people.pickle'
                ]
            ]]
        else:
            return [[path, [], []]]

    def with_request_dec(func, *args, **kwargs):
        @wraps(func)
        @mock.patch('json.dump')
        @mock.patch('os.walk', side_effect=mock_os_walk_side_effect)
        @mock.patch('json.load', side_effect=load_side_effect)
        @mock.patch('flask.request')
        @mock.patch('builtins.open')
        @mock.patch('endpoints.CiscoSparkAPI')
        @mock.patch('os.path.exists')
        @mock.patch('os.makedirs')
        @mock.patch('os.remove')
        @mock.patch('matplotlib.pyplot.savefig')
        @mock.patch('shutil.rmtree')
        @mock.patch('random.random', return_value=random)
        def closure(mock_random, mock_rm_tree, mock_savefig, mock_remove, mock_makedirs, mock_exists,
                    mock_api, mock_open, mock_flask, mock_load, mock_oswalk, mock_dump, *args, **kwargs):
            # mock exists
            mock_exists.return_value = True

            # mock flask
            flask.request.json={'data': data}

            # mock load
            # Project config, People, Commands, admins
            # mock_load.side_effect = [project, people, commands, admins]
            # mock_load.side_effect = [project, people, queue, global_stats, commands, admins]

            # mock api
            mock2 = mock.MagicMock()
            mock2.id = ME_ID
            mock2.displayName = 'QueueBot'

            mock1 = mock.MagicMock()
            mock1.people.me.return_value = mock2
            mock1.people.get.side_effect = api_get_side_effect
            # mock1.people.get.return_value = mock_people

            # mock message id
            message_mock = mock.MagicMock()
            message_mock.id = data.get('id')
            message_mock.personId = data.get('personId')
            message_mock.roomId = data.get('roomId')
            message_mock.text = data.get('text')
            mock1.messages.get.return_value = message_mock

            mock_api.return_value = mock1

            return func(*args, **kwargs)
        return closure

    return with_request_dec


def unit_test(func):
    og_open = open

    config.DATA_FOLDER = 'queuebot/unit_test_data/{}'
    config.SUBPROJECT_FOLDER = config.DATA_FOLDER + '/{}'
    config.QUEUE_FILE = config.SUBPROJECT_FOLDER + '/queue.pickle'
    config.GLOBAL_STATS_FILE = config.SUBPROJECT_FOLDER + '/global-stats.pickle'
    config.ADMINS_FILE = config.DATA_FOLDER + '/admins.pickle'
    config.PEOPLE_FILE = config.SUBPROJECT_FOLDER + '/people.pickle'
    config.COMMANDS_FILE = config.SUBPROJECT_FOLDER + '/commands.pickle'
    config.WARNINGS_FILE = config.DATA_FOLDER + '/warnings.json'
    config.SETTINGS_FILE = config.DATA_FOLDER + '/settings.json'

    @wraps(func)
    @mock.patch('endpoints.CiscoSparkAPI')
    @mock.patch('random.random')
    def mock_all(mock_random, mock_api, *args, **kwargs):

        from queuebot import Bot
        import endpoints

        TOKEN = config.QUEUE_BOT if config.PRODUCTION else config.DEV_QUEUE_BOT
        BOT = Bot(endpoints.CiscoSparkAPI(TOKEN), {
            'roomId': 'UNIT_TEST_ROOMID'
        })
        BOT.initialize_data(project='UNIT_TEST_PROJECT', subproject='UNIT_TEST_SUBPROJECT')
        return func(bot=BOT, *args, **kwargs)

    return mock_all