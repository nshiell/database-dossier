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

from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.Qt import QStandardItemModel, QTextDocument, QStandardItem
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import database_dossier.syntax_highlighter
from .ui import *
from . import syntax_highlighter
from .store import *
from .updater import show_please_update
from .database import ConnectionList, DatabaseException, test_connection

class MainWindow(QMainWindow, WindowMixin):
    table_views = [
        'table_view_data',
        'table_view_schema',
        'table_view_result_set_1',
        'table_view_result_set_2',
        'table_view_result_set_3'
    ]


    @property
    def record_set_colors(self):
        self._record_set_colors = {
            'null' : QVariant(QColor(
                Qt.darkYellow if self.is_dark else Qt.gray
            )),
            'error'  : QVariant(QColor(Qt.red)),
            'number' : QVariant(QColor(
                Qt.green if self.is_dark else Qt.darkGreen
            )),
            'date'   : QVariant(QColor(255, 0, 255))
        }

        return self._record_set_colors


    def __init__(self):
        super().__init__()

        # The order of setups is important
        self.set_window_icon_from_artwork('database-dossier.png')
        self.load_xml('main_window.ui')
        self.extra_ui_file_name = 'extra.ui'
        self.result_sets = {}
        self.diagram = None
        self.connection_dialog = ConnectionDialog(self, test_connection)
        self.setup_text_editor()
        self.setup()
        self._record_set_colors = None


    def setup_result_set(self, name):
        self.result_sets[name] = TableModel(self.record_set_colors)
        table_view = self.f('table_view_' + name)
        table_view.setModel(self.result_sets[name])
        table_view.setContextMenuPolicy(Qt.CustomContextMenu)

        table_view.customContextMenuRequested.connect(lambda:
            self.extra_ui.get_menu_action('action_result_set').exec_(
                QCursor.pos()
            )
        )


    def copy_cell(self):
        table_view = self.f(
            self.table_views[self.tab_result_sets.currentIndex()]
        )

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
        if new_index == 2:
            self.text_edit_log_document.setHtml(
            syntax_highlighter.highlight(
                self.text_edit_log.toPlainText(),
                self.formatter_log
            )
        )


    def setup_diagram(self):
        self.diagram = Diagram(self.web_view_diagram)
        self.diagram.bind('selected', self.show_table_schema)
        self.diagram.bind('context_menu_table', lambda pos, table_name:
            print(table_name)
        )

        self.diagram.bind('state_change', self.connections.store_active_diagram)
        self.diagram.setup()

        colors = self.palette().color
        self.diagram.page_colors = {
            'thumbBackgroundColor'      : colors(QPalette.ToolTipBase).name(),
            'thumbBackgroundColorHover' : colors(QPalette.Link).name(),
            'thumbBorderColorHover'     : colors(QPalette.Link).name(),
        }


    def show_diagram(self, new_index):
        if new_index != 1:
            return None

        if self.diagram == None:
            self.setup_diagram()

        self.show_schema_in_diagram()


    def show_schema_in_diagram(self):
        cons = self.connections

        try:
            self.diagram.populate(
                schema             = cons.active_schema,
                position_overrides = cons.active_database_positions,
                colors             = cons.active_table_colors
            )
        except DatabaseException:
            return None


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


    def tree_select_changed(self, table, database, connection):
        if connection:
            self.f('db_name').setText(connection)

            if table:
                self.show_table(table)

            if database:
                self.f('connection_indicator').setText(database)
                if self.diagram:
                    self.show_schema_in_diagram()
        else:
            self.f('db_name').setText('')
            self.f('connection_indicator').setText('')


    def show_table(self, table_name, show_schema = False):
        max_records = 1000
        table_name_clean = repr(table_name)[1:-1]

        self.execute_update_table_model(
            self.result_sets['schema'],
            "DESCRIBE %s" % table_name_clean
        )

        self.execute_update_table_model(
            self.result_sets['data'],
            "SELECT * FROM %s LIMIT %d" % (table_name_clean, max_records)
        )

        self.tab_result_sets.setTabText(0, 'Data: %s (%d)' % (
            table_name,
            max_records
        ))

        if show_schema:
            self.tab_result_sets.setCurrentIndex(1)
        else:
            self.tab_result_sets.setCurrentIndex(0)


    def show_table_schema(self, table_name):
        self.show_table(table_name, True)


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
        self.last_tree_model_index = None
        self.connections = ConnectionList(
            self.state.connections,
            self.tree_view_objects
        )

        self.connections.is_dark = self.is_dark
        self.connections.bind('focus_changed', lambda names: self.tree_select_changed(**names))
        self.connections.bind('log_line', self.log_line)
        #self.connections.bind('connection_changed', self.f('connection_indicator').setText)
        #self.connections.bind('database_changed', self.f('db_name').setText)
        self.connections.bind('errors', self.error_handler)

        index = self.state.active_connection_index
        if index is not None and index >= len(self.state.connections):
            index = None

        self.connections.active_connection_index = index

        self.tree_view_objects.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view_objects.customContextMenuRequested.connect(
            self.tree_context_menu
        )


    def tree_context_menu(self, pos):
        index = self.tree_view_objects.indexAt(pos)
        if index.parent().isValid():
            return None

        self.last_tree_model_index = index
        self.extra_ui.get_menu_action('tree_connection').exec_(QCursor.pos())


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

        self.text_editor = TextEditor(self, self.text_edit_sql, syntax_highlighter)

        context_menu = self.extra_ui.get_menu_action('editor')

        self.text_editor.bind('context_menu', lambda pos:
            context_menu.exec_(pos)
        )

        self.text_editor.bind('text_cursor_moved', lambda line_no:
            self.f('line_no').setText('Line: ' + str(line_no))
        )

        self.text_editor.bind('updated', update_cb)

        border_color = self.palette().color(QPalette.Link).name()
        self.text_editor.bind('focus_in', lambda:
            self.change_style(self.tab_editor, [('border', '1px solid ' + border_color, False)])
        )
        self.text_editor.bind('focus_out', lambda:
            self.change_style(self.tab_editor, [('border', '1px solid black', False)])
        )

        self.bind_menu(self.extra_ui, '_extra')


    def add_statusbar(self):
        self.statusBar().addPermanentWidget(self.extra_ui.frame_statusbar, 1)


    def copy_name(self):
        index = self.tree_view_objects.currentIndex()
        QApplication.instance().clipboard().setText(index.data())


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
        window.menu('action_connection_remove' + s, self.remove_connection)
        window.menu('action_refresh' + s, lambda: self.connections.refresh())

        window.menu('action_help' + s, HelpDialog(window, user_config_file_path).show)
        window.menu('action_donate' + s, DonationDialog(window).show)
        window.menu('action_about' + s, AboutDialog(window).show)


    def remove_connection(self):
        confirmation = show_confirm_remove_connection(self.last_tree_model_index.data())
        if confirmation == QMessageBox.Ok:
            self.connections.pop(self.last_tree_model_index.row())


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
        self.bind_menu(self.extra_ui, '_tree_connection')

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
        self.table_query.currentChanged.connect(self.show_diagram)


        # Must be last
        self.setup_state()


    def show(self):
        super().show()
        show_please_update()


    def closeEvent(self, event):
        sql = self.text_edit_sql.toPlainText()
        self.state.editor_sql = sql
        self.state.connections = self.connections
        self.state.active_connection_index = self.connections.active_connection_index

        save_state(self.state)
