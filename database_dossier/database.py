import json
import mysql.connector
from PyQt5.QtWidgets import *
from PyQt5.Qt import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class DatabaseException(Exception): pass
class QueryDatabaseException(DatabaseException): pass


class ConnectionList(list):
    def __init__(self, connections, q_tree):
        self.extend(connections)

        self.model = QStandardItemModel()
        self.q_tree = q_tree
        self.q_tree.setModel(self.model)

        self.q_tree.clicked.connect(self.tree_click)
        self.event_bindings = {}
        self._active_connection_index = None


    def trigger(self, event_name, args):
        if event_name in self.event_bindings:
            self.event_bindings[event_name](args)


    @property
    def active_connection(self):
        return self[self._active_connection_index]


    @property
    def active_connection_index(self):
        return self._active_connection_index


    @active_connection_index.setter
    def active_connection_index(self, active_connection_index):
        self._active_connection_index = active_connection_index
        self.draw_state()


    def draw_state(self):
        errors = []
        create_connection_items(self.model.invisibleRootItem(), self, errors)
        if errors:
            self.trigger('errors', errors)

        try:
            update_tree_state(self)
        except QueryDatabaseException as e:
            self.trigger('errors', ([str(e)],))

    def tree_click(self, model_index):
        connection_item = thingy
        database_item = thingy
        table_item = thingy


    def bind(self, event_name, event_callback):
        self.event_bindings[event_name] = event_callback


    def execute_active_connection_cursor(self, sql):
        """
        if not self.active_connection:
            raise QueryDatabaseException('No connection')
        """

        if self.active_connection['broken']: # test!
            raise QueryDatabaseException('No connection')

        cursor = self.active_connection['db_connection'].cursor()
        try:
            cursor.execute(sql)
        except mysql.connector.errors.Error as e:
            raise QueryDatabaseException(str(e))

        return cursor


def list_databases(lst, connection_item):
    for x in lst.execute_active_connection_cursor('SHOW DATABASES;'):
        connection_item.appendRow(DatabaseTreeItem(name=x[0]))

    lst.q_tree.expand(connection_item.index())


def list_tables(lst, database_item):
    for x in lst.execute_active_connection_cursor('SHOW TABLES;'):
        database_item.appendRow(TableTreeItem(name=x[0]))

    lst.q_tree.expand(database_item.index())


def escape(text):
    return json.dumps(text)[1:-1]


def change_database(lst, db_name):
    lst.execute_active_connection_cursor('USE %s;' % escape(db_name))


def update_tree_state(lst):
    if lst._active_connection_index is None:
        return None

    connection_item = lst.model.invisibleRootItem().child(lst._active_connection_index)
    connection_item.status = TreeItem.status_selected
    list_databases(lst, connection_item)

    if 'database' in lst.active_connection:
        database_name = lst.active_connection['database']
        if database_name:
            if lst.active_connection and database_name:
                change_database(lst, database_name)
                for i in range(connection_item.rowCount()):
                    database_item = connection_item.child(i)
                    if database_item.text() == database_name:
                        database_item.status = TreeItem.status_selected
                        list_tables(lst, database_item)

                        table_name = lst.active_connection['table']
                        if table_name:
                            for j in range(database_item.rowCount()):
                                table_item = database_item.child(j)
                                if table_item.text() == table_name:
                                    table_item.status = TreeItem.status_selected
                                    lst.trigger('table_changed', table_name)

                        return None


def name_from_connection_data(data):
    return '%s@%s:%s' % (data['user'], data['host'], data['port'])


def create_db_connection(**kwargs):
    allowed = ['host', 'password', 'user', 'port']
    new_kwargs = {k: v for k, v in kwargs.items() if k in allowed}

    new_kwargs['autocommit'] = True
    new_kwargs['auth_plugin'] = 'mysql_native_password'

    return mysql.connector.connect(**new_kwargs)


def create_connection_items(root_node, lst, errors):
    for connection_data in lst:
        connection_data['broken'] = False

        name = name_from_connection_data(connection_data)
        if [c for c in lst if 'name' in c and c['name'] == name]: continue
        connection_data['name'] = name

        tree_item = ConnectionTreeItem(**connection_data)
        root_node.appendRow(tree_item)

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
        'selected' : 'white'
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
