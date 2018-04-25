import json
import os
import pprint
import re
import shutil

from app import logger, DEFAULT_SUBPROJECT
from config import PROJECT_CONFIG, DATA_FOLDER, SUBPROJECT_FOLDER, SETTINGS_FILE
from queuebot.commands import CommandManager
from queuebot.people import PeopleManager
from queuebot.queue import Queue
from queuebot.admins import AdminManager


class ProjectManager:
    def __init__(self, api, roomId): # , people_manager):
        self._api = api
        self._file = PROJECT_CONFIG
        self._subproject_folder = SUBPROJECT_FOLDER
        self._roomId = roomId
        # self._people = people_manager

        if not os.path.exists(self._file):
            self._project_config = {}
            self._save()
        else:
            self._project_config = json.load(open(self._file, 'r'))

        self._project = self.get_project(roomId)
        self._settings_file = SETTINGS_FILE.format(self.get_project())

        if os.path.exists(self._settings_file):
            self._settings = json.load(open(self._settings_file, 'r'))
        else:
            self._settings = {}

    def get_project(self, roomId=None):
        if not os.path.exists(self._file):
            return None
        elif not roomId:
            return getattr(self, '_project', None)
        else:
            for project, room in self._project_config:
                if roomId == room:
                    return project
            else:
                return None

    def get_projects(self):
        return set([i[0] for i in self._project_config])

    def get_subprojects(self, project=None):

        if not project and getattr(self, '_subprojects', None):
            return self._subprojects
        elif not project:
            target_project = self.get_project()
        else:
            target_project = project

        subprojects = set()

        for parent, folders, files in os.walk(os.path.dirname(os.path.dirname(os.path.realpath(self._subproject_folder)))):
            for project in folders:
                if project == target_project:
                    subprojects = sorted(set([x[1] for x in os.walk(os.path.join(parent, project))][0]))
                    break
            break

        if not project:
            self._subprojects = subprojects

        return subprojects

    @property
    def config(self):
        return self._project_config

    def get_commands(self, project=None, subproject=None):
        if not project and not subproject:
            # global set
            global_set = []
            for i in self.get_projects():
                for j in self.get_subprojects(project=i):
                    global_set += self._get_managers(project=i, subproject=j)['commands'].get_commands()
            return global_set
        elif subproject and not project:
            return []
        elif project and not subproject:
            # global set
            global_set = []
            for j in self.get_subprojects(project=project):
                global_set += self._get_managers(project=project, subproject=j)['commands'].get_commands()
            return global_set
        else:
            return self._get_managers(project=project, subproject=subproject)['commands'].get_commands()

    def _get_managers(self, project, subproject):
        people = PeopleManager(self._api, project=project, subproject=subproject)
        admins = AdminManager(self._api, project=project, people_manager=people)
        q = Queue(self._api, project=project, subproject=subproject, people_manager=people)
        commands = CommandManager(self._api, project=project, subproject=subproject, people_manager=people)

        return {
            'people': people,
            'admins': admins,
            'queue': q,
            'commands': commands
        }

    def create_new_project(self, project, roomId):

        self._project = project.upper()
        self._settings_file = SETTINGS_FILE.format(project.upper())

        if os.path.exists(self._settings_file):
            self._settings = json.load(open(self._settings_file, 'r'))
        else:
            self._settings = {}

        if project.upper() in self.get_projects():
            return False
        else:
            self._project_config.append(tuple([project.upper(), None]))
            self.create_subproject(name=DEFAULT_SUBPROJECT, default=True)
            self._save()
            return True

    def create_subproject(self, name, default=False):
        subproject_name = name.upper()
        os.makedirs(self._subproject_folder.format(self.get_project(), subproject_name), exist_ok=True)
        if default:
            self._settings['default_subproject'] = subproject_name
            self._save_settings()

    def delete_subproject(self, name):
        subproject_name = name.upper()
        if self._settings['default_subproject'] != subproject_name:
            shutil.rmtree(self._subproject_folder.format(self.get_project(), subproject_name), ignore_errors=True)
            return True
        else:
            return False

    def set_default_subproject(self, subproject):
        if subproject in self.get_subprojects():
            self._settings['default_subproject'] = subproject.upper()
            self._save_settings()
            return True
        else:
            return False

    def get_default_subproject(self):
        return self._settings.get('default_subproject')

    @property
    def strict_regex(self):
        return self._settings.get('strict_regex')

    @strict_regex.setter
    def strict_regex(self, value):
        self._settings['strict_regex'] = value
        self._save_settings()

    def register_room_to_project(self, project, roomId):
        # Verify user is an admin on the target project
        # TODO:
        if project.upper() in self.get_projects():
            if self.get_project(roomId) == project.upper():
                return False, "This bot is already registered to project '" + str(project.upper()) + "'"
            else:
                # Unregister from any previous project
                self._project_config = [i for i in self._project_config if i[1] != roomId and
                                        i != tuple([project.upper(), None])]

                self._project = project.upper()
                self._project_config.append(tuple([self.get_project(), roomId]))
                self._save()
                return True, ''
        else:
            return False, "ERROR: project '" + str(project.upper()) + "' has not been created."

    def delete_project(self):
        self._project_config = [i for i in self._project_config if i[0] != self.get_project()]
        self._save()
        shutil.rmtree(DATA_FOLDER.format(self.get_project()), ignore_errors=True)
        self._project = None

    # def get_admins(self):
    #     return self._admins
    #
    # def is_admin(self, id):
    #     return id in self._admins + GLOBAL_ADMINS
    #
    # def is_global_admin(self, id):
    #     return id in GLOBAL_ADMINS

    def _save(self):
        logger.debug(pprint.pformat(self._project_config))
        json.dump(self._project_config, open(self._file, 'w'), indent=4, separators=(',', ': '))

    def _save_settings(self):
        logger.debug(pprint.pformat(self._settings))
        json.dump(self._settings, open(self._settings_file.format(self.get_project()), 'w'))

    # def add_admin(self, id):
    #     logger.debug("Adding admin '" + id + "'")
    #
    #     self._admins.append(id)
    #
    #     if self._people.get_person(id):
    #         self._people.update_person(
    #             id=id,
    #             admin=True
    #         )
    #     self._save()
    #
    # def remove_admin(self, id):
    #     logger.debug("Removing admin '" + id + "'")
    #
    #     self._admins = [i for i in self._admins if i != id]
    #
    #     if self._people.get_person(id):
    #         self._people.update_person(
    #             id=id,
    #             admin=False
    #         )
    #     self._save()
