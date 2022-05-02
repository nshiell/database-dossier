import mysql.connector
from PyQt5.QtWidgets import *
from PyQt5.Qt import QStandardItemModel, QTextDocument, QStandardItem
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from .ui import *
from . import syntax_highlighter
from .store import *


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
        except mysql.connector.errors.Error as e:
            show_connection_error(str(e))
            return None
        
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


class DatabaseMixin:
    def __init__(self):
        super().__init__()
        self.connections = []
        self.connection_labels = []
        self.active_connection_index = None
        self._previous_connection_index = None
        self.db_names_selected = {}


    def execute_create_cursor(self, sql):
        if not self.active_connection:
            raise mysql.connector.errors.Error('No connection')

        cursor = self.active_connection.cursor()
        cursor.execute(sql)

        return cursor


    def update_activation(self):
        self.disable_previous_connection()
        self.enable_active_connection()


    def disable_previous_connection(self):
        connection_changed = (
            self.previous_connection_index is not None and
            self.previous_connection_index != self.active_connection_index
        )

        if connection_changed:
            con_item = self.tree_model.item(self.previous_connection_index)
            con_item.setEnabled(False)

            i = 0
            while con_item.child(i):
                con_item.child(i).setEnabled(False)
                j = 0
                while con_item.child(i).child(j):
                    con_item.child(i).child(j).setEnabled(False)
                    j+= 1
                i+= 1


    def enable_active_connection(self):
        connection_changed = (
            self.previous_connection_index != self.active_connection_index
        )

        if connection_changed:
            con_item = self.tree_model.item(self.active_connection_index)
            con_item.setEnabled(True)

            i = 0
            while con_item.child(i):
                con_item.child(i).setEnabled(True)
                j = 0
                while con_item.child(i).child(j):
                    con_item.child(i).child(j).setEnabled(True)
                    j+= 1
                i+= 1


    def add_connection(self, connection):
        self.connections.append(connection)
        self.previous_connection_index = self.active_connection_index
        self.active_connection_index = len(self.connections) - 1

        name = '%s@%s:%s' % (
            connection.user,
            connection.server_host,
            connection.server_port
        )

        root_node = self.tree_model.invisibleRootItem()

        connection_item = create_connection_tree_item(name)
        root_node.appendRow(connection_item)

        for x in self.execute_active_connection_cursor('SHOW DATABASES;'):
            connection_item.appendRow(create_database_tree_item(x[0]))

        self.f('tree_view_objects').expand(connection_item.index())


    @property
    def active_connection(self):
        if self.active_connection_index is None:
            return None

        return self.connections[self.active_connection_index]

    """
    @property
    def previous_connection(self):
        if self.previous_connection_index is None:
            return None

        return self.connections[self.previous_connection_index]
    """

    def create_db_connection(self, **kwargs):
        kwargs['autocommit'] = True
        kwargs['auth_plugin'] = 'mysql_native_password'

        return mysql.connector.connect(**kwargs)


    def show_connection_error(self, text):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(text)
        msg.setWindowTitle("Error")
        msg.exec_()


    def show_connection_ok(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("Ok")
        msg.setInformativeText('Can connect')
        msg.setWindowTitle("OK")
        msg.exec_()


    def duplicate_connection_dialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Ok")
        msg.setInformativeText('This connection has already been established')
        msg.setWindowTitle("OK")
        msg.exec_()


    def is_connection_already_defined(self, **kwargs):
        if self.tree_model.item(0):
            name = '%s@%s:%s' % (
            kwargs['user'],
            kwargs['host'],
            kwargs['port']
        )
        i = 0
        while self.tree_model.item(i):
            if name == self.tree_model.item(i).text():
                return True
            i+= 1

        return False

    def add_connection_and_activate(self, **kwargs):
        if self.is_connection_already_defined(**kwargs):
            self.duplicate_connection_dialog()
            return False
 
        try:
            self.add_connection(self.create_db_connection(**kwargs))
        except mysql.connector.errors.Error as e:
            self.show_connection_error(str(e))
            return False

        self.update_activation()

        return True


    def test_connection(self, **kwargs):
        try:
            self.create_db_connection(**kwargs)
        except mysql.connector.errors.Error as e:
            self.show_connection_error(str(e))
            return None

        self.show_connection_ok()


class MainWindow(DatabaseMixin, QMainWindow, WindowMixin):
    def __init__(self):
        super().__init__()
        self.set_window_icon_from_artwork('database-dossier.png')
        self.load_xml('main_window.ui')
        self.result_sets = {}
        self.setup_text_editor()
        self.setup()


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
        cursor = self.execute_create_cursor(sql)
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
        except mysql.connector.errors.Error as e:
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


    @property
    def is_dark(self):
        color = self.palette().color(QPalette.Background)
        average = (color.red() + color.green() + color.blue()) / 3

        return average <= 128


    def flash_tab(self, tab_index):
        q_tab_bar = self.f('tab_result_sets').tabBar()
        old_color = q_tab_bar.tabTextColor(tab_index)

        new_color = QColor('#FFFF66') if self.is_dark else QColor('#444400')
        times = 0

        def change():
            nonlocal times

            if times % 2:
                q_tab_bar.setTabTextColor(tab_index, old_color)
            else:
                q_tab_bar.setTabTextColor(tab_index, new_color)

            if times < 5:
                times+= 1
                QTimer.singleShot(200, change)

        change()


    def select_query(self):
        text_edit_sql = self.f('text_edit_sql')
        doc = text_edit_sql.document()
        text_cursor = text_edit_sql.textCursor()

        start_end_points = doc.get_sql_fragment_start_end_points(text_cursor)
        if start_end_points:
            self.select_sql_fragment(*start_end_points)


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
            result_set_name = 'result_set_' + str(result_set_index + 1)
            tab_index = 2 + result_set_index
            table_model = self.result_sets[result_set_name]
            self.execute_update_table_model(table_model, sql_fragment)
            self.show_record_set(tab_index)

    def show_record_set(self, tab_index):
        self.f('tab_result_sets').setCurrentIndex(tab_index)
        self.f('text_edit_sql').setFocus()
        self.flash_tab(tab_index)


    def tree_item_type_from_index(self, model_index):
        if not model_index.parent().isValid():
            return 'connection'

        if model_index.parent().parent().isValid():
            return 'table'

        return 'database'


    def tree_item_connection_index(self, model_index):
        level = self.tree_item_type_from_index(model_index)

        if level == 'table':
            return model_index.parent().parent().row()

        if level == 'database':
            return model_index.parent().row()

        return model_index.row() # connection


    def change_database_if_needed(self, db_name):        
        change_needed = (
            db_name not in self.db_names_selected or
            self.db_names_selected[self.active_connection_index] != db_name
        )

        if change_needed:
            self.db_names_selected[self.active_connection_index] = db_name
            self.execute_active_connection_cursor(
                "USE %s;" % repr(db_name)[1:-1]
            )

    def select_tree_object(self, model_index):
        level = self.tree_item_type_from_index(model_index)
        new_connection_index = self.tree_item_connection_index(model_index)

        if new_connection_index != self.active_connection_index:
            self.previous_connection_index = self.active_connection_index
            self.active_connection_index = new_connection_index
            self.update_activation()

        if level == 'database':
            database_item = self.tree_model.itemFromIndex(model_index)
            self.change_database_if_needed(model_index.data())

            children_count = database_item.rowCount()

            if children_count:
                for row_num in reversed(range(children_count)):
                    database_item.removeRow(row_num)

            for x in self.execute_active_connection_cursor('SHOW TABLES;'):
                database_item.appendRow(create_table_tree_item(x[0]))

            self.f('tree_view_objects').expand(model_index)
        elif level == 'table':
            self.change_database_if_needed(model_index.parent().data())
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


    def setup_state(self):
        self.state = load_state()
        self.text_editor.plain_text = self.state.editor_sql

        valid_connection_index = (
            self.state.active_connection_index is not None and
            self.state.active_connection_index in self.state.connections
        )

        if valid_connection_index:
            active_conection_state = (
                self.state.connections[self.state.active_connection_index]
            )
            try:
                connection = create_connection(
                    active_conection_state.host,
                    active_conection_state.user,
                    active_conection_state.password,
                    active_conection_state.port
                )

                if connection:
                    self.connect(connection, active_conection_state.password)
            except mysql.connector.errors.DatabaseError as e:
                self.result_sets['data'].headers = ['Error']
                self.result_sets['data'].record_set = [[str(e)]]
                self.result_sets['data'].is_error = True
                self.result_sets['data'].update_emit()
                self.show_record_set(0)


    def setup_text_editor(self):
        def update_cb(can_undo, can_redo): 
            self.get_menu_action('action_undo').setEnabled(can_undo)
            self.get_menu_action('action_redo').setEnabled(can_redo)

        self.text_editor = TextEditor(self, self.f('text_edit_sql'),
            update_cb=update_cb
        )


    def setup(self):
        connection_dialog = ConnectionDialog(self)
        self.menu('create_connection', connection_dialog.show)
        self.menu('action_undo', self.text_editor.undo)
        self.menu('action_redo', self.text_editor.redo)
        self.menu('action_cut', self.text_editor.q_text.cut)
        self.menu('action_copy', self.text_editor.q_text.copy)
        self.menu('paste', self.text_editor.q_text.paste)
        self.menu('action_select_query', self.select_query)
        self.menu('action_select_all', self.text_editor.q_text.selectAll)

        self.menu('text_size_increase',
            self.text_editor.font_point_size_increase
        )
        self.menu('text_size_descrease',
            self.text_editor.font_point_size_decrease
        )


        def font_choice():
            old_font = QFont(
                self.text_editor.font_name,
                pointSize=self.text_editor.font_point_size,
                italic=self.text_editor.font_italic,
                weight=75 if self.text_editor.font_bold else 50
            )

            new_font, valid = QFontDialog.getFont(QFont(old_font))
            if valid:
                self.text_editor.font = new_font

        self.menu('font', font_choice)

        self.menu('quit', qApp.quit)

        self.setup_result_set('result_set_1')
        self.setup_result_set('result_set_2')
        self.setup_result_set('result_set_3')
        self.setup_result_set('data')
        self.setup_result_set('schema')

        tree_view_objects = self.f('tree_view_objects')
        # Used in other classes!
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
