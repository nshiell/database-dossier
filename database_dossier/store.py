import json
from appdirs import *
from os import path

from pprint import pprint

dirs = AppDirs('database-dossier', 'nshiell')

user_config_file_path = os.path.join(dirs.user_config_dir, 'config.json')


def make_dir_if_not_exists():
    if not os.path.exists(dirs.user_config_dir):
        os.makedirs(dirs.user_config_dir)


def get_config():
    if path.exists(user_config_file_path):
        return json.loads(open(user_config_file_path, "r").read())

    return None


def set_config(data):
    make_dir_if_not_exists()
    json_data = json.dumps(data, indent=4, sort_keys=True)
    open(user_config_file_path, "w").write(json_data)



class State:
    def __init__(self, data={}):
        self.user = data['user'] if 'user' in data else None
        self.password = data['password'] if 'password' in data else None
        self.host = data['host'] if 'host' in data else None
        self.port = data['port'] if 'port' in data else None

    def to_dict(self):
        return {
            "user": self.user,
            "password": self.password,
            "port": self.port,
            "host": self.host
        }

def load_state():
    return State(get_config())

def save_state(state):
    set_config(state.to_dict())



#def 
#user_data_dir


