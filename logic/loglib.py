import os

import yaml
from enum import Enum
from threading import current_thread
from datetime import datetime
import numpy as np
import glm

class LogLevels(Enum) :
    FATAL = 0,
    ERROR = 1,
    WARN = 2,
    INFO = 3

class LogEntry :

    def __init__(self,level,message="",dict_info = {}):
        self.date = datetime.now()
        self.date_string = self.date.strftime("%y-%m-%d %H:%M:%S:%f")[:-3]
        self.thread_name = current_thread().name
        self.level = level
        self.message = message
        self.dict_info = dict(dict_info)

    def read_yaml(cls,fpath):

        text = open(fpath,'r').readlines()
        if text[0].startswith("!!python/object") and text[0].endswith("LogEntry"):
            return yaml.load(text,yaml.Loader)
        else:
            return None

    def save_yaml(cls,entry,folder):

        with open(folder+"/"+entry.date_string+"yaml","w") as file_ref:
            yaml.dump(entry,file_ref)

    def __getitem__(self, item):
        return self.dict_info[item]

class LogManager :

    def __init__(self, folder):
        self.logs = {}
        self.keys = []
        self.get_logs(folder)
        self.get_all_keys()

    def get_logs(self,folder):
        files = sorted(os.listdir(folder))

        existing_logs = [entry.date_string for entry in self.logs]
        for file in files:
            if file not in existing_logs:
                log = LogEntry.read_yaml(folder + "/" + file)
                if log is not None:
                    self.logs[log.date_string]

    def get_all_keys(self):
        allkeys = {}
        for log in self.logs:
            for dict_element in log.dict_info :
                allkeys[dict_element] = 0
        self.keys =  allkeys.keys()





