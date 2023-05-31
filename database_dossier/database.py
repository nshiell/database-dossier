"""
    Database Dossier - A User Interface for your databases
    Copyright (C) 2022  Nicholas Shiell

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
import mysql.connector
from PyQt5.QtWidgets import *
from PyQt5.Qt import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class DatabaseException(Exception): pass
class QueryDatabaseException(DatabaseException): pass


def show_connection_error(text):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText("Error")
    msg.setInformativeText(text)
    msg.setWindowTitle("Error")
    msg.exec_()


def show_connection_ok():
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText("Ok")
    msg.setInformativeText('Can connect')
    msg.setWindowTitle("OK")
    msg.exec_()


def test_connection(**kwargs):
    error = create_db_connection_error(**kwargs)
    if error is not None:
        show_connection_error(error)
    else:
        show_connection_ok()


class ConnectionList(list):
    def __init__(self, connections, q_tree):
        self.extend(connections)

        self.model = QStandardItemModel()
        self.q_tree = q_tree
        self.q_tree.setModel(self.model)

        self.q_tree.clicked.connect(self.tree_click)
        self.event_bindings = {}
        self._active_connection_index = None

        self.last_connection_item = None
        self.last_database_item = None


    @property
    def is_dark(self):
        pass


    @is_dark.setter
    def is_dark(self, is_dark):
        TreeItem.colors['selected'] = 'white' if is_dark else 'black'


    def refresh(self):
        remove_connection_items(self)
        self.draw_state()


    def pop(self, index=None):
        if index == None:
            index = len(self) - 1

        names = {
            'table'      : None,
            'database'   : None,
            'connection' : None
        }

        if self._active_connection_index is not None:
            if index == self._active_connection_index:
                self._active_connection_index = None
                self.last_connection_item = None
                self.last_database_item = None
            elif self._active_connection_index > index:
                self._active_connection_index-= 1
                names['connection'] = self[self._active_connection_index]['name']

        connection = self[index]
        connection['should_remove'] = True
        self.draw_state()
        super().pop(index)
        self.trigger('focus_changed', names)

        return connection


    def trigger(self, event_name, args):
        if event_name in self.event_bindings:
            self.event_bindings[event_name](args)


    @property
    def active_connection(self):
        if self._active_connection_index is None:
            return None

        return self[self._active_connection_index]


    @property
    def active_connection_index(self):
        return self._active_connection_index


    @active_connection_index.setter
    def active_connection_index(self, active_connection_index):
        is_change = self._active_connection_index != active_connection_index
        self._active_connection_index = active_connection_index
        self.draw_state()

        c = self.active_connection
        if is_change and 'broken' in c and not c['broken']:
            names = {'connection': None, 'database': None, 'table': None}
            if 'name' in c:
                names['connection'] = c['name']

            if 'database' in c:
                names['database'] = c['database']

            self.trigger('focus_changed', names)


    def draw_state(self):
        errors = []
        create_connection_items(self.model.invisibleRootItem(), self, errors)
        if errors:
            self.trigger('errors', errors)

        try:
            update_tree_state(self)
        except QueryDatabaseException as e:
            self.trigger('errors', ([str(e)],))


    def list_index_from_name(self, name):
        for i, connection in enumerate(self):
            if 'name' in connection and connection['name'] == name:
                return i

        return None


    def tree_click(self, model_index):
        names = find_connection_database_table_from_index(model_index)

        index_list = self.list_index_from_name(names['connection'])
        if index_list is not None and not self[index_list]['broken']:
            if names['database']:
                self[index_list]['database'] = names['database']

            self.active_connection_index = index_list
            self.trigger('focus_changed', names)


    def is_active_connection_broken(self):
        if 'broken' not in self.active_connection:
            return False

        return self.active_connection['broken']


    def bind(self, event_name, event_callback):
        self.event_bindings[event_name] = event_callback


    def execute_active_connection_cursor(self, sql):
        if not self.active_connection:
            raise QueryDatabaseException('No connection')

        if self.active_connection['broken']:
            raise QueryDatabaseException('No connection')

        try:
            cursor = self.active_connection['db_connection'].cursor()
            cursor.execute(sql)
        except mysql.connector.errors.Error as e:
            raise QueryDatabaseException(str(e))

        return cursor


    @property
    def active_schema(self):
        sql = '''
            SELECT
                tables.table_name,
                ref_con.referenced_table_name,
                key_column_usage.column_name,
                ref_con.constraint_name

                FROM
                    information_schema.tables AS tables

                    LEFT JOIN
                        information_schema.referential_constraints AS ref_con ON
                            ref_con.constraint_schema = tables.table_schema AND
                            tables.table_name = ref_con.table_name

                    LEFT JOIN information_schema.key_column_usage as key_column_usage ON
                        ref_con.constraint_schema = key_column_usage.table_schema
                            AND ref_con.table_name = key_column_usage.table_name
                            AND ref_con.constraint_name = key_column_usage.constraint_name

                WHERE
                    information_schema.tables.table_schema = '%s';
        '''

        tables = {}
        results = self.execute_active_connection_cursor(sql % self.active_connection['database'])
        for result in results:
            if result[0] not in tables:
                tables[result[0]] = {}

            if result[1]:
                if result[1] not in tables[result[0]]:
                    tables[result[0]][result[1]] = {}

                if result[2] not in tables[result[0]][result[1]]:
                    tables[result[0]][result[1]][result[2]] = {}

                tables[result[0]][result[1]][result[2]] = result[3]

        return tables



def list_databases(lst, connection_item):
    if connection_item.rowCount() == 0:
        for x in lst.execute_active_connection_cursor('SHOW DATABASES;'):
            connection_item.appendRow(DatabaseTreeItem(name=x[0]))

        lst.q_tree.expand(connection_item.index())


def list_tables(lst, database_item):
    if database_item.rowCount() == 0:
        for x in lst.execute_active_connection_cursor('SHOW TABLES;'):
            database_item.appendRow(TableTreeItem(name=x[0]))

        lst.q_tree.expand(database_item.index())


def escape(text):
    return json.dumps(text)[1:-1]


def change_database(lst, db_name):
    lst.execute_active_connection_cursor('USE %s;' % escape(db_name))


def select_connection(lst, connection_item):
    connection_item.status = TreeItem.status_selected

    if lst.last_connection_item and lst.last_connection_item != connection_item:
        lst.last_connection_item.status = TreeItem.status_normal
    lst.last_connection_item = connection_item


def select_database(lst, database_item):
    database_item.status = TreeItem.status_selected

    if lst.last_database_item and lst.last_database_item != database_item:
        lst.last_database_item.status = TreeItem.status_normal
    lst.last_database_item = database_item


def update_tree_state(lst):
    if lst._active_connection_index is None:
        return None

    connection_item = lst.model.invisibleRootItem().child(lst._active_connection_index)
    if not lst.is_active_connection_broken():
        select_connection(lst, connection_item)

        list_databases(lst, connection_item)

        if 'database' in lst.active_connection:
            database_name = lst.active_connection['database']
            if database_name:
                if lst.active_connection and database_name:
                    change_database(lst, database_name)
                    for i in range(connection_item.rowCount()):
                        database_item = connection_item.child(i)
                        if database_item.text() == database_name:
                            select_database(lst, database_item)
                            list_tables(lst, database_item)
                            return None


def name_from_connection_data(data):
    return '%s@%s:%s' % (data['user'], data['host'], data['port'])


def create_db_connection_error(**kwargs):
    try:
        create_db_connection(**kwargs)
    except mysql.connector.errors.Error as e:
        return str(e)

    return None

def create_db_connection(**kwargs):
    allowed = ['host', 'password', 'user', 'port']
    new_kwargs = {k: v for k, v in kwargs.items() if k in allowed}

    new_kwargs['autocommit'] = True
    new_kwargs['auth_plugin'] = 'mysql_native_password'

    return mysql.connector.connect(**new_kwargs)


def remove_connection_items(lst):
    lst.last_connection_item = None
    lst.last_database_item = None

    for connection_data in lst:
        lst.model.removeRow(0)
        connection_data['should_remove'] = None
        connection_data['q_tree_item'] = None
        connection_data['broken'] = None


def create_connection_items(root_node, lst, errors):
    for i, connection_data in enumerate(lst):
        name = name_from_connection_data(connection_data)
        if 'should_remove' in connection_data and connection_data['should_remove']:
            lst.model.removeRow(i)
            continue

        connection_data['broken'] = False

        if 'q_tree_item' in connection_data and connection_data['q_tree_item']: continue

        connection_data['name'] = name

        tree_item = ConnectionTreeItem(**connection_data)
        root_node.appendRow(tree_item)
        connection_data['q_tree_item'] = tree_item

        try:
            connection_data['db_connection'] = create_db_connection(**connection_data)
        except mysql.connector.errors.Error as e:
            connection_data['broken'] = True
            tree_item.status = TreeItem.status_broken
            errors.append([str(e)])


class FontGettersSetters:
    @property
    def italic(self):
        return self.font().italic()


    @italic.setter
    def italic(self, is_italic):
        font = self.font()
        font.setItalic(is_italic)
        self.setFont(font)

    @property
    def bold(self):
        return self.font().bold()


    @bold.setter
    def bold(self, is_bold):
        font = self.font()
        font.setBold(is_bold)
        self.setFont(font)


    @property
    def font_point_size(self, size):
        return self.font().pointSize()


    @font_point_size.setter
    def font_point_size(self, size):
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)


    @property
    def font_family(self):
        return self.font().family()


    @font_family.setter
    def font_family(self, family):
        font = self.font()
        font.setFamily(family)
        self.setFont(font)


class TreeItem(QStandardItem, FontGettersSetters):
    status_broken   = 'broken'
    status_normal   = 'normal'
    status_selected = 'selected'

    colors = {
        'broken'   : 'red',
        'normal'   : 'grey',
        'selected' : None # Set is runtime so it can work in dar/light themes
    }

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.setEditable(False)
        self.setText(kwargs['name'])
        self.status = self.status_normal
        self.font_family = 'Open Sans'


    @property
    def status(self):
        return self._status


    @status.setter
    def status(self, value):
        self._status = value
        self.setForeground(QColor(self.colors[value]))
        self.bold = value == self.status_selected
        self.italic = value == self.status_broken


class ConnectionTreeItem(TreeItem):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.font_point_size = 13


class DatabaseTreeItem(TreeItem):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.font_point_size = 11


class TableTreeItem(TreeItem):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.font_point_size = 9


def find_connection_database_table_from_index(model_index):
    names = {
        'table'      : None,
        'database'   : None,
        'connection' : None
    }

    level = item_type_from_index(model_index)
    if level == 'table':
        names['table'] = model_index.data()
        names['database'] = model_index.parent().data()
        names['connection'] = model_index.parent().parent().data()
    elif level == 'database':
        names['database'] = model_index.data()
        names['connection'] = model_index.parent().data()
    else: # connection
        names['connection'] = model_index.data()

    return names
    #print(model_index.row())

def item_type_from_index(model_index):
    if not model_index.parent().isValid():
        return 'connection'

    if model_index.parent().parent().isValid():
        return 'table'

    return 'database'
