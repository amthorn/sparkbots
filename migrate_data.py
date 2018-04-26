import glob
import json
import re
import os
import time

from collections import defaultdict
from config import DATA_FOLDER

# pickle_files = glob.glob("queuebot/data/")

FOR_REAL = True

new_project_config = []

for parent, folders, files in os.walk('queuebot/data'):
    for file in files:
        if file == 'people.pickle':
            print(parent)
            if FOR_REAL:
                data = json.load(open(os.path.join(parent, file)))
                for person in data:
                    person['timesInQueue'] = []
                    person['timesAtHead'] = []

                json.dump(data, open(os.path.join(parent, file), 'w'), indent=4, separators=(',', ': '))

