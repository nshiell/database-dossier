"""
    Database Dossier - A User Interface for your databases
    Copyright (C) 2023  Nicholas Shiell

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

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


def valid(container, key, data_type, min_size=None, max_size=None):
    if key not in container:
        return False

    if not isinstance(container[key], data_type):
        return False

    if type(container[key]) != data_type:
        return False

    if data_type == str:
        len_string = len(container[key])

        if max_size is not None and len_string > max_size:
            return False

        if min_size is not None and len_string < min_size:
            return False
    elif data_type == int:
        if max_size is not None and container[key] > max_size:
            return False

        if min_size is not None and container[key] < min_size:
            return False
    elif data_type == list:
        if  max_size is not None and len(container[key]) > max_size:
            return False

    return True


class State:
    def parse_connection(self, connection):
        self.connections.append({
            'user': connection['user']
                if valid(connection, 'user', str, 0, 200) else None,

            'password': connection['password']
                if valid(connection, 'password', str, 0, 200) else None,

            'host': connection['host']
                if valid(connection, 'host', str, 0, 200) else None,

            'port': connection['port']
                if valid(connection, 'port', int, 0, 10000) else 3306,

            'database': connection['database']
                if valid(connection, 'database', str, 0, 200) else None,

            'table': connection['table']
                if valid(connection, 'table', str, 0, 200) else None,

            'diagram': connection['diagram']
                if valid(connection, 'diagram', dict) else None,
        })


    def __init__(self, data={}):
        self.editor_sql = None
        self.sql_path = os.path.join(dirs.user_data_dir, 'editor.sql')
        self.connections = []
        self.active_connection_index = None

        if isinstance(data, dict):
            if valid(data, 'connections', list, 0, 50):
                for connection in data['connections']:
                    if isinstance(connection, dict):
                        self.parse_connection(connection)

            # Todo test
            active_connection_index_valid = valid(
                data,
                'active_connection_index',
                int,
                0,
                len(self.connections)
            )

            if active_connection_index_valid:
                self.active_connection_index = data['active_connection_index']

            if 'sql_path' in data and data['sql_path'] is str:
                self.sql_path = data['sql_path']
            else:
                self.sql_path = os.path.join(dirs.user_data_dir, 'editor.sql')

            if self.sql_path and os.path.exists(self.sql_path):
                self.editor_sql = open(self.sql_path, "r").read()


    def connections_for_persist(self):
        options_allowed = [
            'host',
            'password',
            'user',
            'port',
            'database',
            'table',
            'diagram'
        ]

        cons = []
        for con in self.connections:
            cons.append({k: v for k, v in con.items() if k in options_allowed})

        return cons


    def to_dict(self):
        return {
            "version": '0.0.1',
            "connections": self.connections_for_persist(),
            "sql_path": self.sql_path,
            "active_connection_index": self.active_connection_index
        }


def load_state():
    return State(get_config())


def save_state(state):
    set_config(state.to_dict())

    sql_dir = os.path.split(state.sql_path)[0]
    if not os.path.exists(sql_dir):
        os.makedirs(sql_dir)

    save_editor_sql(state.sql_path, state.editor_sql)