from PyQt5.QtWidgets import *
from PyQt5.Qt import QStandardItemModel, QTextDocument, QStandardItem
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from .ui import *
from . import syntax_highlighter
from .store import *
from .database import (
    ConnectionList,
    DatabaseException,
    create_db_connection_error
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


class HelpDialog(QDialog, WindowMixin):
    def __init__(self, main_win):
        super().__init__(main_win)
        self._doc_dir = None
        self.setup = False

    def show(self):
        """
        Setting up the URL is expensive
        do it lazily here - rather than on __init__
        """
        if not self.setup:
            self.resize(QSize(600, 300))
            self.load_xml('help.ui')
            self.web_view.setUrl(QUrl('file://' + self.doc_dir + '/help.html'))
            self.web_view.loadFinished.connect(self.load_finished)
            self.setup = True

        super().show()


    def load_finished(self, is_ok):
        print(self.web_view.page().mainFrame().evaluateJavaScript("from_app(7)"))
        self.web_view.page().mainFrame().addToJavaScriptWindowObject('app', self)


    @pyqtSlot(str)
    def response(self, value):
        print(value)


    @property
    def doc_dir(self):
        if not self._doc_dir:
            path = os.path.realpath(__file__)
            path = os.path.dirname(path) # parent
            path = os.path.dirname(path) # parent
            self._doc_dir = os.path.join(path, 'doc')

        return self._doc_dir


class AboutDialog(QDialog, WindowMixin):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.setFixedSize(QSize(600, 300))
        self.load_xml('about.ui')


class ConnectionDialog(QDialog, WindowMixin):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.setFixedSize(QSize(300, 140))
        self.load_xml('connection.ui')

        self.test.clicked.connect(lambda:
            main_win.test_connection(**self.connection_dict)
        )

        self.bind('button_box.Ok', 'clicked', self.add)
        self.bind('button_box.Cancel', 'clicked', self.close)


    def add(self):
        connected = self.parent().add_connection_activate(
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


class MainWindow(QMainWindow, WindowMixin):
    def __init__(self):
        super().__init__()

        # The order of setups is important
        self.set_window_icon_from_artwork('database-dossier.png')
        self.load_xml('main_window.ui')
        self.extra_ui_file_name = 'extra.ui'
        self.result_sets = {}
        self.connection_dialog = ConnectionDialog(self)
        self.about_dialog = AboutDialog(self)
        self.help_dialog = HelpDialog(self)
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


    def test_connection(self, **kwargs):
        error = create_db_connection_error(**kwargs)
        if error is not None:
            show_connection_error(error)
        else:
            show_connection_ok()


    def copy_cell(self):
        table_views = [
            'table_view_data',
            'table_view_schema',
            'table_view_result_set_1',
            'table_view_result_set_2',
            'table_view_result_set_3'
        ]

        table_view = self.f(table_views[self.tab_result_sets.currentIndex()])

        QApplication.instance().clipboard().setText(str(
            table_view.currentIndex().data()
        ))


    def log_line(self, sql):
        old_text = self.text_edit_log.toPlainText()
        prefix = '\n' if self.text_edit_log.toPlainText() else ''
        self.text_edit_log.setText(old_text + prefix + sql)


    def execute_update_table_model(self, table_model, sql):
        table_model.is_error = False
        table_model.headers = ['Result']
        table_model.record_set = [['OK']]

        try:
            cursor = self.connections.execute_active_connection_cursor(sql)
            if cursor.description:
                table_model.headers = [i[0] for i in cursor.description]
                table_model.record_set = cursor.fetchall()
        except DatabaseException as e:
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

        new_color = QColor('black') if self.is_dark else QColor('white')
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


    def tree_item_connection_index(self, model_index):
        level = self.tree_item_type_from_index(model_index)

        if level == 'table':
            return model_index.parent().parent().row()

        if level == 'database':
            return model_index.parent().row()

        return model_index.row() # connection


    def table_changed(self, table_name):
        table_name_clean = repr(table_name)[1:-1]

        self.execute_update_table_model(
            self.result_sets['schema'],
            "DESCRIBE %s" % table_name_clean
        )

        self.execute_update_table_model(
            self.result_sets['data'],
            "SELECT * FROM %s LIMIT %d" % (table_name_clean, 1000)
        )

        self.tab_result_sets.setTabText(0, 'Data: ' + table_name)


    def error_handler(self, errors):
        self.result_sets['data'].headers = ['Error']
        self.result_sets['data'].record_set = errors
        self.result_sets['data'].is_error = True
        self.result_sets['data'].update_emit()
        self.show_record_set(0)


    def add_connection_activate(self, **kwargs):
        self.connections.append(kwargs)
        self.connections.active_connection_index = len(self.connections) - 1

        return True


    def setup_connections(self):
        self.connections = ConnectionList(
            self.state.connections,
            self.tree_view_objects
        )

        self.connections.bind('table_changed', self.table_changed)
        self.connections.bind('log_line', self.log_line)
        self.connections.bind('connection_changed', self.f('connection_indicator').setText)
        self.connections.bind('database_changed', self.f('db_name').setText)
        self.connections.bind('errors', self.error_handler)

        self.connections.active_connection_index = self.state.active_connection_index

        self.tree_view_objects.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view_objects.customContextMenuRequested.connect(lambda:
            self.extra_ui.get_menu_action('tree_database').exec_(
                QCursor.pos()
            )
        )


    def setup_state(self):
        self.state = load_state()
        self.setup_connections()
        
        self.text_editor.plain_text = self.state.editor_sql


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


    def copy_name(self):
        position = self.tree_view_objects.mapToGlobal(QCursor.pos())
        
        index = self.tree_view_objects.currentIndex()
        print(index.data())
        #model = self.tree_view_objects.model()
        #item = model.itemFromIndex(self.tree_view_objects.indexAt(QCursor.pos()))
        #print(self.tree_view_objects.indexAt(QCursor.pos()).data())
        QApplication.instance().clipboard().setText(
            self.tree_view_objects.indexAt(QCursor.pos()).data()
        )


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
        window.menu('action_copy_item_name' + s, self.copy_name)


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
        self.bind_menu(self.extra_ui, '_tree')

        self.setup_result_set('result_set_1')
        self.setup_result_set('result_set_2')
        self.setup_result_set('result_set_3')
        self.setup_result_set('data')
        self.setup_result_set('schema')

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
