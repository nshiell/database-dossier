import mysql.connector
from PyQt5.QtWidgets import *
from PyQt5.Qt import QStandardItemModel, QTextDocument, QStandardItem
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from .ui import *
from . import syntax_highlighter
from .store import *



def create_connection_tree_item_broken(name):
    font = QFont('Open Sans', 12)
    font.setBold(True)
    font.setItalic(True)

    item = QStandardItem()
    item.setEditable(False)
    item.setFont(font)
    item.setText(name)
    item.setBackground(QColor('black'))
    item.setForeground(QColor('red'))

    return item


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
    def __init__(self, main_win):
        super().__init__(main_win)

        self.setFixedSize(QSize(300, 140))
        self.load_xml('connection.ui')

        self.test.clicked.connect(lambda: main_win.test_connection(
            **self.connection_dict
        ))

        self.bind('button_box.Ok', 'clicked', self.add)
        self.bind('button_box.Cancel', 'clicked', self.close)


    def add(self):
        connected = self.parent().add_connection_and_activate(
            **self.connection_dict
        )

        if connected:
            self.close()


    @property
    def connection_dict(self):
        return {
            'host'     : self.host.text(),
            'port'     : int(self.port.text()),
            'user'     : self.user.text(),
            'password' : self.password.text()
        }


class DatabaseMixin:
    def __init__(self):
        super().__init__()
        self.connections = []
        self.previous_connection_index = None
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
        needs_disabling = (
            self.previous_connection_index is not None and
            self.previous_connection_index != self.state.active_connection_index
        )

        if needs_disabling:
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
        if self.previous_connection_index != self.state.active_connection_index:
            con_item = self.tree_model.item(self.state.active_connection_index)
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


    def add_broken_connection(self, **connection):
        self.connections.append(connection)
        name = '%s@%s:%s' % (
            connection['user'],
            connection['host'],
            connection['port']
        )

        root_node = self.tree_model.invisibleRootItem()

        connection_item = create_connection_tree_item_broken(name)
        root_node.appendRow(connection_item)
        return connection_item


    @property
    def active_connection_name(self):
        # can't use self.active_connection - recursion!
        if self.state.active_connection_index is None:
            return None

        connection = self.connections[self.state.active_connection_index]

        return '%s@%s:%s' % (
            connection.user,
            connection.server_host,
            connection.server_port
        )


    def add_connection(self, connection):
        self.connections.append(connection)
        self.previous_connection_index = self.state.active_connection_index

        name = '%s@%s:%s' % (
            connection.user,
            connection.server_host,
            connection.server_port
        )

        root_node = self.tree_model.invisibleRootItem()

        connection_item = create_connection_tree_item(name)
        root_node.appendRow(connection_item)
        return connection_item

    def list_databases(self, connection_item):
        for x in self.execute_active_connection_cursor('SHOW DATABASES;'):
            connection_item.appendRow(create_database_tree_item(x[0]))

        self.tree_view_objects.expand(connection_item.index())


    @property
    def active_connection(self):
        if self.state.active_connection_index is None:
            return None

        # Use the old method f() here
        self.f('connection_indicator').setText(self.active_connection_name)

        return self.connections[self.state.active_connection_index]


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
            connection_item = self.add_connection(
                self.create_db_connection(**kwargs)
            )
            self.list_databases(connection_item)
        except mysql.connector.errors.Error as e:
            self.show_connection_error(str(e))
            return False

        self.state.connections.append(kwargs)
        self.state.active_connection_index = len(self.connections) - 1
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

        # The order of setups is important
        self.set_window_icon_from_artwork('database-dossier.png')
        self.load_xml('main_window.ui')
        self.extra_ui_file_name = 'extra.ui'
        self.result_sets = {}
        self.connection_dialog = ConnectionDialog(self)
        self.setup_text_editor()
        self.setup()


    def setup_result_set(self, name):
        self.result_sets[name] = TableModel()
        table_view = self.f('table_view_' + name)
        table_view.setModel(self.result_sets[name])
        table_view.setContextMenuPolicy(Qt.CustomContextMenu)

        table_view.customContextMenuRequested.connect(lambda:
            self.extra_ui.get_menu_action('action_result_set').exec_(
                QCursor.pos()
            )
        )


    def copy_cell(self):
        table_views = [
            'table_view_data',
            'table_view_schema',
            'table_view_result_set_1',
            'table_view_result_set_2',
            'table_view_result_set_3'
        ]

        table_view = self.f(table_views[self.tab_result_sets.currentIndex()])

        QApplication.instance().clipboard().setText(
            table_view.currentIndex().data()
        )
        


    def log_line(self, sql):
        old_text = self.text_edit_log.toPlainText()
        prefix = '\n' if self.text_edit_log.toPlainText() else ''
        self.text_edit_log.setText(old_text + prefix + sql)


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

        prefix = '\n' if self.text_edit_log.toPlainText() else ''

        self.text_edit_log.setText(
            self.text_edit_log.toPlainText() + prefix + sql
        )

        table_model.update_emit()


    def highlight_log(self, new_index):
        if new_index == 1:
            self.text_edit_log_document.setHtml(
            syntax_highlighter.highlight(
                self.text_edit_log.toPlainText(),
                self.formatter_log
            )
        )


    def select_sql_fragment(self, start_point, end_point):
        text_cursor = self.text_edit_sql.textCursor()
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
        
        self.text_edit_sql.setTextCursor(text_cursor)


    @property
    def is_dark(self):
        color = self.palette().color(QPalette.Background)
        average = (color.red() + color.green() + color.blue()) / 3

        return average <= 128


    def flash_tab(self, tab_index):
        q_tab_bar = self.tab_result_sets.tabBar()
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
        doc = self.text_edit_sql.document()
        text_cursor = self.text_edit_sql.textCursor()

        start_end_points = doc.get_sql_fragment_start_end_points(text_cursor)
        if start_end_points:
            self.select_sql_fragment(*start_end_points)


    def execute(self, result_set_index):
        doc = self.text_edit_sql.document()
        text_cursor = self.text_edit_sql.textCursor()

        selected_sql = text_cursor.selectedText()

        if selected_sql:
            sql_fragment = selected_sql.strip()
        else:
            start_end_points = doc.get_sql_fragment_start_end_points(
                text_cursor
            )

            if start_end_points is None:
                return None

            sql_fragment = self.text_edit_sql.toPlainText()[
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
        self.tab_result_sets.setCurrentIndex(tab_index)
        self.text_edit_sql.setFocus()
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
            self.db_names_selected[self.state.active_connection_index] != db_name
        )

        if change_needed:
            self.db_names_selected[self.state.active_connection_index] = db_name
            self.execute_active_connection_cursor(
                "USE %s;" % repr(db_name)[1:-1]
            )
        self.f('db_name').setText(db_name)


    def select_tree_object(self, model_index):
        level = self.tree_item_type_from_index(model_index)
        new_connection_index = self.tree_item_connection_index(model_index)

        if isinstance(self.connections[new_connection_index], dict):
            return None

        if new_connection_index != self.state.active_connection_index:
            self.previous_connection_index = self.state.active_connection_index
            self.state.active_connection_index = new_connection_index
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

            self.tree_view_objects.expand(model_index)
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


            name = '%s@%s:%s::%s.%s' % (
                self.active_connection.user,
                self.active_connection.server_host,
                self.active_connection.server_port,
                self.db_names_selected[self.state.active_connection_index],
                table_name
            )


            self.tab_result_sets.setTabText(0, 'Data: ' + table_name)
        else: # connection
            connection_item = self.tree_model.itemFromIndex(model_index)

            children_count = connection_item.rowCount()

            if children_count:
                for row_num in reversed(range(children_count)):
                    connection_item.removeRow(row_num)

            self.list_databases(connection_item)

    def setup_state(self):
        self.state = load_state()
        self.text_editor.plain_text = self.state.editor_sql

        errors = []
        for index, connection_data in enumerate(self.state.connections):
            if self.is_connection_already_defined(**connection_data):
                continue

            try:
                connection_item = self.add_connection(
                    self.create_db_connection(**connection_data)
                )

                if index == self.state.active_connection_index:
                    self.list_databases(connection_item)
                else:
                    connection_item.setEnabled(False)

            except mysql.connector.errors.Error as e:
                self.add_broken_connection(**connection_data).setEnabled(False)
                errors.append([str(e)])

        if errors:
            self.result_sets['data'].headers = ['Error']
            self.result_sets['data'].record_set = errors
            self.result_sets['data'].is_error = True
            self.result_sets['data'].update_emit()
            self.show_record_set(0)

        self.previous_connection_index = None
        self.update_activation()


    def setup_text_editor(self):
        def update_cb(can_undo, can_redo): 
            self.action_undo.setEnabled(can_undo)
            self.action_redo.setEnabled(can_redo)
            self.extra_ui.action_undo_extra.setEnabled(can_undo)
            self.extra_ui.action_redo_extra.setEnabled(can_redo)


        def text_cursor_moved_cb(line_no):
            self.f('line_no').setText('Line: ' + str(line_no))

        self.text_editor = TextEditor(self, self.text_edit_sql,
            update_cb=update_cb,
            text_cursor_moved_cb=text_cursor_moved_cb,
            context_menu=self.extra_ui.get_menu_action('editor')
        )

        self.bind_menu(self.extra_ui, '_extra')


    def add_statusbar(self):
        self.statusBar().addPermanentWidget(self.extra_ui.frame_statusbar, 1)


    def bind_menu(self, window=None, s=''):
        if not window:
            window = self

        e = self.text_editor
        window.menu('action_create_connection' + s, self.connection_dialog.show)
        window.menu('action_undo' + s, self.text_editor.undo)
        window.menu('action_redo' + s, self.text_editor.redo)
        window.menu('action_cut' + s, self.text_editor.q_text.cut)
        window.menu('action_copy' + s, self.text_editor.q_text.copy)
        window.menu('action_paste' + s, self.text_editor.q_text.paste)
        window.menu('action_select_query' + s, self.select_query)
        window.menu('action_select_all' + s, self.text_editor.q_text.selectAll)
        window.menu('action_text_size_increase' + s, e.font_point_size_increase)
        window.menu('action_text_size_decrease' + s, e.font_point_size_decrease)
        window.menu('action_font' + s, self.show_font_choice)
        window.menu('action_quit' + s, self.quit)
        window.menu('action_copy_cell' + s, self.copy_cell)


    def quit(self):
        self.closeEvent(None)
        qApp.quit()


    def show_font_choice(self):
        old_font = QFont(
            self.text_editor.font_name,
            pointSize=self.text_editor.font_point_size,
            italic=self.text_editor.font_italic,
            weight=75 if self.text_editor.font_bold else 50
        )

        new_font, valid = QFontDialog.getFont(QFont(old_font))
        if valid:
            self.text_editor.font = new_font


    def setup(self):
        self.add_statusbar()
        self.bind_menu()
        self.bind_menu(self.extra_ui, '_result_set')

        self.setup_result_set('result_set_1')
        self.setup_result_set('result_set_2')
        self.setup_result_set('result_set_3')
        self.setup_result_set('data')
        self.setup_result_set('schema')

        # Used in other classes!
        self.tree_model = QStandardItemModel()
        self.tree_view_objects.setModel(self.tree_model)
        self.tree_view_objects.clicked.connect(self.select_tree_object)

        self.formatter_log = syntax_highlighter.create_formatter(
            self.text_edit_log.styleSheet()
        )
        self.text_edit_log_document = QTextDocument(self)
        self.text_edit_log_document.setDefaultStyleSheet(
            syntax_highlighter.style()
        )
        self.text_edit_log.setDocument(self.text_edit_log_document)

        self.execute_1.clicked.connect(lambda: self.execute(0))
        self.execute_2.clicked.connect(lambda: self.execute(1))
        self.execute_3.clicked.connect(lambda: self.execute(2))
        self.table_query.currentChanged.connect(self.highlight_log)

        # Must be last
        self.setup_state()


    def closeEvent(self, event):
        sql = self.text_edit_sql.toPlainText()
        self.state.editor_sql = sql
        
        save_state(self.state)
