import json
import mysql.connector
from PyQt5.QtWidgets import *
from PyQt5.Qt import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class DatabaseException(Exception): pass
class QueryDatabaseException(DatabaseException): pass
class ConnectionDatabaseException(DatabaseException): pass


class ConnectionList(list):
    def __init__(self, connections, q_tree, active_index=None):
        self.extend(connections)
        self.previous_index = None
        self.active_index = active_index
        self.model = QStandardItemModel()
        self.q_tree = q_tree
        self.q_tree.setModel(self.model)

        self.q_tree.clicked.connect(self.tree_click)
        self.event_bindings = {}


    def bind(self, event_name, event_callback):
        self.event_bindings[event_name] = event_callback


    def tree_click(self, model_index):
        level = tree_item_type_from_index(model_index)
        new_connection_index = tree_item_connection_index(model_index)

        if new_connection_index != self.active_index:
            self.previous_index = self.active_index
            self.active_index = new_connection_index
            update_activation(self)

        if level == 'connection':
            tree_selected_connection(self, model_index)
        elif level == 'database':
            tree_selected_database(self, model_index)
        else:
            tree_selected_table(self, model_index)


    def update_tree_and_get_errors(self):
        return update_tree(self)


    def execute_active_connection_cursor(self, sql):
        cursor = self.execute_create_cursor(sql)

        if 'log_line' in self.event_bindings:
            self.event_bindings['log_line'](sql)

        return cursor


    def execute_create_cursor(self, sql):
        if not self.active_connection:
            raise ConnectionDatabaseException()

        is_boken = (
            'broken' in self.active_connection and
            self.active_connection['broken']
        )

        if is_boken:
            raise ConnectionDatabaseException()

        cursor = self.active_connection['connection'].cursor()
        try:
            cursor.execute(sql)
        except mysql.connector.errors.ProgrammingError as e:
            raise QueryDatabaseException(str(e))
        return cursor


    @property
    def active_connection(self):
        if self.active_index is None:
            return None

        connection = self[self.active_index]

        if 'connection_changed' in self.event_bindings:
            self.event_bindings['connection_changed'](connection['name'])
            self.event_bindings['database_changed'](connection['database'])

        return connection


def tree_item_type_from_index(model_index):
    if not model_index.parent().isValid():
        return 'connection'

    if model_index.parent().parent().isValid():
        return 'table'

    return 'database'


def create_table_tree_item(name):
    item = QStandardItem()
    item.setEditable(False)
    item.setText(name)

    return item


def tree_selected_database(lst, model_index):
    database_item = lst.model.itemFromIndex(model_index)
    change_database_if_needed(lst, model_index.data())

    children_count = database_item.rowCount()

    if children_count:
        for row_num in reversed(range(children_count)):
            database_item.removeRow(row_num)

    for x in lst.execute_active_connection_cursor('SHOW TABLES;'):
        database_item.appendRow(create_table_tree_item(x[0]))

    lst.q_tree.expand(model_index)


def tree_selected_connection(lst, model_index):
    connection_item = lst.model.itemFromIndex(model_index)

    children_count = connection_item.rowCount()

    if children_count:
        for row_num in reversed(range(children_count)):
            connection_item.removeRow(row_num)

    list_databases(lst, connection_item)


def change_database_if_needed(lst, db_name):
    if lst.active_connection['database'] != db_name:
        change_database(lst, db_name)
        lst.active_connection['database'] = db_name

        if 'database_changed' in lst.event_bindings:
            lst.event_bindings['database_changed'](db_name)


def escape(text):
    return json.dumps(text)[1:-1]


def change_database(lst, db_name):
    lst.execute_active_connection_cursor('USE %s;' % escape(db_name))


def tree_selected_table(lst, model_index):
    change_database_if_needed(lst, model_index.parent().data())

    if 'table_changed' in lst.event_bindings:
        lst.event_bindings['table_changed'](model_index.data())


def tree_item_connection_index(model_index):
    level = tree_item_type_from_index(model_index)

    if level == 'table':
        return model_index.parent().parent().row()

    if level == 'database':
        return model_index.parent().row()

    return model_index.row() # connection


def update_tree(lst):
    errors = []
    root_node = lst.model.invisibleRootItem()
    connection_options_allowed = ['host', 'password', 'user', 'port']
    for index, connection_data in enumerate(lst):
        connection_data['broken'] = False
        connection_data['name'] = '%s@%s:%s' % (
            connection_data['user'],
            connection_data['host'],
            connection_data['port']
        )

        if is_connection_already_defined(lst.model, **connection_data):
            continue

        connection_options = {k: v for k, v in connection_data.items() if k in connection_options_allowed}
        try:
            lst[index]['connection'] = create_db_connection(
                **connection_options
            )
        except mysql.connector.errors.Error as e:
            connection_data['broken'] = True
            errors.append([str(e)])

        if connection_data['database']:
            try:
                change_database(lst, connection_data['database'])

                if 'database_changed' in lst.event_bindings and lst.active_index is not None and lst.active_index == index:
                    lst.event_bindings['database_changed'](connection_data['database'])

            except DatabaseException as e:
                errors.append([str(e)])

        connection_item = create_connection_item(**connection_data)
        root_node.appendRow(connection_item)

        if not connection_data['broken']:
            lst.previous_index = lst.active_index

            if index == lst.active_index:
                list_databases(lst, connection_item)
            else:
                connection_item.setEnabled(False)

    lst.previous_index = None
    update_activation(lst)

    return errors


# todo rewrite
def is_connection_already_defined(model, **kwargs):
    if model.item(0):
        name = create_connection_item(**kwargs)

    i = 0
    while model.item(i):
        if name == model.item(i).text():
            return True
        i+= 1

    return False


def create_connection_item(**kwargs):
    font = QFont('Open Sans', 12)
    font.setBold(True)

    item = QStandardItem()
    item.setEditable(False)
    item.setText(kwargs['name'])

    if 'broken' in kwargs and kwargs['broken']:
        font.setItalic(True)
        item.setBackground(QColor('black'))
        item.setForeground(QColor('red'))

    item.setFont(font)

    return item


def create_db_connection(**kwargs):
    kwargs['autocommit'] = True
    kwargs['auth_plugin'] = 'mysql_native_password'

    return mysql.connector.connect(**kwargs)


def list_databases(lst, connection_item):
    for x in lst.execute_active_connection_cursor('SHOW DATABASES;'):
        connection_item.appendRow(create_database_tree_item(x[0]))

    lst.q_tree.expand(connection_item.index())


def create_database_tree_item(name):
    font = QFont()
    font.setBold(True)

    item = QStandardItem()
    item.setEditable(False)
    item.setFont(font)
    item.setText(name)

    return item


def update_activation(lst):
    disable_previous_connection(lst)
    enable_active_connection(lst)


def disable_previous_connection(lst):
    needs_disabling = (
        lst.previous_index is not None and
        lst.previous_index != lst.active_index
    )

    if needs_disabling:
        con_item = lst.model.item(lst.previous_index)
        con_item.setEnabled(False)

        i = 0
        while con_item.child(i):
            con_item.child(i).setEnabled(False)
            j = 0
            while con_item.child(i).child(j):
                con_item.child(i).child(j).setEnabled(False)
                j+= 1
            i+= 1


def enable_active_connection(lst):
    if lst.previous_index != lst.active_index:
        con_item = lst.model.item(lst.active_index)
        if con_item:
            con_item.setEnabled(True)

            i = 0
            while con_item.child(i):
                con_item.child(i).setEnabled(True)
                j = 0
                while con_item.child(i).child(j):
                    con_item.child(i).child(j).setEnabled(True)
                    j+= 1
                i+= 1
