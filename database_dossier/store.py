import json
from appdirs import *
from os import path

dirs = AppDirs('database-dossier', 'nshiell')

user_config_file_path = os.path.join(dirs.user_config_dir, 'config.json')

def make_config_dir_if_not_exists():
    if not os.path.exists(dirs.user_config_dir):
        os.makedirs(dirs.user_config_dir)


def get_config():
    if path.exists(user_config_file_path):
        return json.loads(open(user_config_file_path, "r").read())

    return None


def set_config(data):
    make_config_dir_if_not_exists()
    json_data = json.dumps(data, indent=4, sort_keys=True)
    open(user_config_file_path, "w").write(json_data)


def save_editor_sql(sql_path, editor_sql):
    if editor_sql == None:
        editor_sql = ''
    open(sql_path, "w").write(editor_sql)


class State:
    def __init__(self, data={}):
        if data == None:
            self.user = None
            self.password = None
            self.host = None
            self.port = None
            self.sql_path = os.path.join(dirs.user_data_dir, 'editor.sql')
            self.editor_sql = None
        else:
            self.user = data['user'] if 'user' in data else None
            self.password = data['password'] if 'password' in data else None
            self.host = data['host'] if 'host' in data else None
            self.port = data['port'] if 'port' in data else None
    
            if 'sql_path' in data:
                self.sql_path = data['sql_path']
            else:
                self.sql_path = os.path.join(dirs.user_data_dir, 'editor.sql')
            
            if os.path.exists(self.sql_path):
                self.editor_sql = open(self.sql_path, "r").read()
            else:
                self.editor_sql = None


    def to_dict(self):
        return {
            "user": self.user,
            "password": self.password,
            "port": self.port,
            "host": self.host,
            "sql_path": self.sql_path
        }

def load_state():
    return State(get_config())

def save_state(state):
    set_config(state.to_dict())

    sql_dir = os.path.split(state.sql_path)[0]
    if not os.path.exists(sql_dir):
        os.makedirs(sql_dir)

    save_editor_sql(state.sql_path, state.editor_sql)


#def 
#user_data_dir


