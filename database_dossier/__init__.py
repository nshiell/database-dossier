import mysql.connector
from PyQt5.QtWidgets import *
from PyQt5.Qt import QStandardItemModel, QTextDocument, QStandardItem
from PyQt5.QtGui import QTextCursor, QIcon, QFont
from PyQt5.QtCore import *
from .ui import *
from . import syntax_highlighter
from .store import *


def create_connection(host, user, password, port):
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        auth_plugin='mysql_native_password',
        port=port,
        autocommit=True
    )


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


def create_connection_tree_item(name):
    font = QFont('Open Sans', 12)
    font.setBold(True)

    item = QStandardItem()
    item.setEditable(False)
    item.setFont(font)
    item.setText(name)

    return item


def create_database_tree_item(name):
    font = QFont()
    font.setBold(True)

    item = QStandardItem()
    item.setEditable(False)
    item.setFont(font)
    item.setText(name)

    return item


def create_table_tree_item(name):
    item = QStandardItem()
    item.setEditable(False)
    item.setText(name)

    return item


class ConnectionDialog(QDialog, WindowMixin):
    def __init__(self, parent):
        super().__init__(parent)

        self.setFixedSize(QSize(300, 140))
        self.load_xml('connection.ui')

        self.bind('test', 'clicked', lambda: self.create_connection(True))
        
        self.bind('button_box.Cancel', 'clicked', self.close)
        self.bind('button_box.Ok', 'clicked', self.create_connection)


    def create_connection(self, dry_run = False):
        password = self.f('password').text()

        try:
            connection = create_connection(
                self.f('host').text(),
                self.f('user').text(),
                password,
                self.f('port').text()
            )
        except mysql.connector.errors.DatabaseError as e:
            show_connection_error(str(e))
        
        if dry_run:
            show_connection_ok()
        else:
            self.parent().connect(connection, password)
            self.close()


def create_connection(host, user, password, port):
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        auth_plugin='mysql_native_password',
        port=port,
        autocommit=True
    )


class MainWindow(QMainWindow, WindowMixin):
    def __init__(self):
        super().__init__()
        self.set_window_icon_from_artwork('database-dossier.png')
        self.load_xml('main_window.ui')
        self.connections = []
        self.active_connection_index = 0
        self.result_sets = {}
        self.text_editor = None
        self.setup()


    @property
    def active_connection(self):
        return self.connections[self.active_connection_index]


    def setup_result_set(self, name):
        self.result_sets[name] = TableModel()
        table_view = self.f('table_view_' + name)
        table_view.setModel(self.result_sets[name])
        table_view.setContextMenuPolicy(Qt.CustomContextMenu)

        def context_menu(point):
            index = table_view.indexAt(point)
            menu = QMenu(self)
            action1 = QAction(QIcon("edit-copy"), "&Copy")
            action1.triggered.connect(lambda:
                # @todo fixme!
                app.clipboard().setText(index.data())
            )

            menu.addAction(action1)
            menu.exec_(QCursor.pos())

        table_view.customContextMenuRequested.connect(context_menu)


    def log_line(self, sql):
        text_edit_log = self.f('text_edit_log')
        old_text = text_edit_log.toPlainText()
        prefix = '\n' if old_text else ''
        text_edit_log.setText(old_text + prefix + sql)


    def execute_active_connection_cursor(self, sql):
        cursor = self.active_connection.cursor()
        cursor.execute(sql)
        self.log_line(sql)
        return cursor


    def execute_update_table_model(self, table_model, sql):
        table_model.is_error = False
        table_model.headers = ['Result']
        table_model.record_set = [['OK']]

        try:
            cursor = self.execute_active_connection_cursor(sql)
            if cursor.description:
                table_model.headers = [i[0] for i in cursor.description]
                table_model.record_set = cursor.fetchall()
        except mysql.connector.errors.ProgrammingError as e:
            table_model.headers = ['Error']
            table_model.record_set = [[str(e)]]
            table_model.is_error = True

        text_edit_log = self.f('text_edit_log')
        prefix = '\n' if text_edit_log.toPlainText() else ''

        text_edit_log.setText(
            text_edit_log.toPlainText() + prefix + sql
        )

        table_model.update_emit()


    def highlight_log(self, new_index):
        if new_index == 1:
            self.text_edit_log_document.setHtml(
            syntax_highlighter.highlight(
                self.f('text_edit_log').toPlainText(),
                self.formatter_log
            )
        )


    def select_sql_fragment(self, start_point, end_point):
        text_cursor = self.f('text_edit_sql').textCursor()
        text_cursor.selectedText()
        current_position = text_cursor.position()
        
        text_cursor.clearSelection()
        text_cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)

        # last char
        text_cursor.movePosition(
            QTextCursor.Right,
            QTextCursor.MoveAnchor,
            end_point
        )

        #Legnth
        text_cursor.movePosition(
            QTextCursor.Left,
            QTextCursor.KeepAnchor,
            end_point - start_point
        )

        text_cursor.selectedText()
        
        self.f('text_edit_sql').setTextCursor(text_cursor)



    def execute(self, result_set_index):
        text_edit_sql = self.f('text_edit_sql')
        doc = text_edit_sql.document()
        text_cursor = text_edit_sql.textCursor()

        selected_sql = text_cursor.selectedText()

        if selected_sql:
            sql_fragment = selected_sql.strip()
        else:
            start_end_points = doc.get_sql_fragment_start_end_points(
                text_cursor
            )

            if start_end_points is None:
                return None

            sql_fragment = text_edit_sql.toPlainText()[
                start_end_points[0]:start_end_points[1]
            ].strip()

            if sql_fragment:
                self.select_sql_fragment(*start_end_points)

        if sql_fragment:
            text_edit_sql.setFocus()

            result_set_name = 'result_set_' + str(result_set_index + 1)
            table_model = self.result_sets[result_set_name]
            self.execute_update_table_model(table_model, sql_fragment)
            self.f('tab_result_sets').setCurrentIndex(2 + result_set_index)

            text_edit_sql.setFocus()


    def select_tree_object(self, model_index):
        if model_index.parent().isValid():
            if model_index.parent().parent().isValid():
                level = 'table'
            else:
                level = 'database'
        else:
            level = 'connection'

        if level == 'database':
            database_item = self.tree_model.itemFromIndex(model_index)
            self.active_connection_index = model_index.parent().row()
            self.execute_active_connection_cursor(
                "USE %s;" % repr(model_index.data())[1:-1]
            )

            children_count = database_item.rowCount()

            if children_count:
                for row_num in reversed(range(children_count)):
                    database_item.removeRow(row_num)

            for x in self.execute_active_connection_cursor('SHOW TABLES;'):
                database_item.appendRow(create_table_tree_item(x[0]))

            self.f('tree_view_objects').expand(model_index)
        elif level == 'table':
            self.active_connection_index = model_index.parent().parent().row()
            cursor = self.active_connection.cursor()

            table_name = model_index.data()
            table_name_clean = repr(table_name)[1:-1]

            self.execute_update_table_model(
                self.result_sets['schema'],
                "DESCRIBE %s" % table_name_clean
            )

            self.execute_update_table_model(
                self.result_sets['data'],
                "SELECT * FROM %s LIMIT %d" % (table_name_clean, 1000)
            )

            self.f('tab_result_sets').setTabText(0, 'Table: ' + table_name)
        elif level == 'connection':
            self.active_connection_index = model_index.row()


    def list_databases(self):
        root_node = self.tree_model.invisibleRootItem()

        name = '%s:%s' % (
            self.active_connection.server_host,
            self.active_connection.server_port
        )
        connection_item = create_connection_tree_item(name)
        root_node.appendRow(connection_item)

        for x in self.execute_active_connection_cursor('SHOW DATABASES;'):
            connection_item.appendRow(create_database_tree_item(x[0]))

        self.f('tree_view_objects').expand(connection_item.index())


    def connect(self, connection, password):
        self.connections.append(connection)
        self.active_connection_index = len(self.connections) - 1

        state_change = (
            self.state.host != connection.server_host or
            self.state.port != connection.server_port or
            self.state.user != connection.user or
            self.state.password != password
        )

        if state_change:
            self.state.host = connection.server_host
            self.state.port = connection.server_port
            self.state.user = connection.user
            self.state.password = password
    
            save_state(self.state)
        
        self.list_databases()


    def setup_state(self):
        self.state = load_state()
        self.text_editor.plain_text = self.state.editor_sql

        if self.state.host:
            try:
                connection = create_connection(
                    self.state.host,
                    self.state.user,
                    self.state.password,
                    self.state.port
                )
                self.connect(connection, self.state.password)
            except mysql.connector.errors.DatabaseError as e:
                show_connection_error(str(e))


    def setup(self):
        connection_dialog = ConnectionDialog(self)
        self.menu('create_connection', connection_dialog.show)

        self.text_editor = TextEditor(self,
            self.f('text_edit_sql'),
            lambda can_undo, can_redo: (
                self.get_menu_action('action_undo').setEnabled(can_undo),
                self.get_menu_action('action_redo').setEnabled(can_redo)
            )
        )

        self.menu('action_undo', self.text_editor.undo)
        self.menu('action_redo', self.text_editor.redo)
        
        
        self.menu('quit', qApp.quit)

        self.setup_result_set('result_set_1')
        self.setup_result_set('result_set_2')
        self.setup_result_set('result_set_3')
        self.setup_result_set('data')
        self.setup_result_set('schema')

        tree_view_objects = self.f('tree_view_objects')
        self.tree_model = QStandardItemModel()
        tree_view_objects.setModel(self.tree_model)

        self.bind(tree_view_objects, 'clicked', self.select_tree_object)

        text_edit_log = self.f('text_edit_log')
        self.formatter_log = syntax_highlighter.create_formatter(text_edit_log.styleSheet())
        self.text_edit_log_document = QTextDocument(self)
        self.text_edit_log_document.setDefaultStyleSheet(syntax_highlighter.style())
        text_edit_log.setDocument(self.text_edit_log_document)


        self.bind('execute_1', 'clicked', lambda: self.execute(0))
        self.bind('execute_2', 'clicked', lambda: self.execute(1))
        self.bind('execute_3', 'clicked', lambda: self.execute(2))
        self.bind('table_query', 'currentChanged', self.highlight_log)

        # Must be last
        self.setup_state()


    def closeEvent(self, event):
        sql = self.f('text_edit_sql').toPlainText()
        self.state.editor_sql = sql
        
        save_state(self.state)
