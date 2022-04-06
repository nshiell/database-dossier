from PyQt5.QtWidgets import *

import mysql.connector

from .ui import *

#from PyQt5.Qt import QStandardItemModel, QStandardItem, QTextDocument
from PyQt5.Qt import QStandardItemModel, QTextDocument
from PyQt5.QtGui import QTextCursor, QIcon
from PyQt5.QtCore import *
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


class ConnectionDialog(QDialog, WindowMixin):
    def __init__(self, parent):
        super().__init__(parent)

        self.setFixedSize(QSize(300, 140))
        self.load_xml('connection.ui')

        self.bind('test', 'clicked', lambda: self.create_connection(True))
        
        self.bind('button_box.Cancel', 'clicked', self.close)
        self.bind('button_box.Ok', 'clicked', self.create_connection)


    def create_connection(self, dry_run = False):
        try:
            connection = create_connection(
                self.f('host').text(),
                self.f('user').text(),
                self.f('password').text(),
                self.f('port').text()
            )

            if dry_run:
                show_connection_ok()
            else:
                self.parent().connect(connection)
                self.close()
            return connection
        except mysql.connector.errors.DatabaseError as e:
            show_connection_error(str(e))


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
        self.load_xml('main_window.ui')
        self.connection = None
        self.result_sets = {}
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


    def highlight_log(self, new_index):
        if new_index == 1:
            self.text_edit_log_document.setHtml(
            syntax_highlighter.highlight(
                self.f('text_edit_log').toPlainText(),
                self.formatter_log
            )
        )


    def on_query_changed(self):
        """Process query edits by user"""
        if self.is_processing_highlighting:
            # If we caused the invokation of this slot by set highlighted
            # HTML text into query editor, then ignore this call and
            # mark highlighting processing as finished.
            self.is_processing_highlighting = False
        else:
            # If changes to text were made by user, mark beginning of
            # highlighting process
            self.is_processing_highlighting = True
            
            text_edit_sql = self.f('text_edit_sql')
            
            
            # Get plain text query and highlight it

            # After we set highlighted HTML back to QTextEdit form
            # the cursor will jump to the end of the text.
            # To avoid that we remember the current position of the cursor.
            current_cursor = text_edit_sql.textCursor()
            current_cursor_position = current_cursor.position()
            # Set highlighted text back to editor which will cause the
            # cursor to jump to the end of the text.

            #highlighted_query_text = highlighted_query_text.replace('z</span>', '</span>')

            self.query_text_edit_document.setHtml(
                syntax_highlighter.highlight(
                    text_edit_sql.toPlainText(),
                    self.formatter
                )
            )
            #print(highlighted_query_text)
            # Return cursor back to the old position
            current_cursor.setPosition(current_cursor_position)
            text_edit_sql.setTextCursor(current_cursor)




    def get_sql_fragment_and_select(self):
        text_edit_sql = self.f('text_edit_sql')
        sql = text_edit_sql.toPlainText()

        if not sql.strip():
            return None

        text_cursor = text_edit_sql.textCursor()
        selected_text = text_cursor.selectedText()
        
        if selected_text:
            return selected_text
        
        
        current_position = text_cursor.position()

        sql_before_cursor = sql[:current_position].rsplit(';', 1)[-1].lstrip()
        sql_after_cursor = sql[current_position:].split(';', 1)[0]

        

        fist_char_after_cursor_is_whitepsace = len(sql_after_cursor) and sql_after_cursor[0].isspace()
        if fist_char_after_cursor_is_whitepsace and not sql_before_cursor:
            return None
        
        
        last_char = sql[current_position + len(sql_after_cursor):current_position + len(sql_after_cursor) + 1]
        
        right_pad = 0
        if last_char == ';':
            right_pad = 1


        #print(cursor.position())
        
        text_cursor.clearSelection()
        
        text_cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
        # last char
        text_cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, current_position + len(sql_after_cursor) + right_pad)
        #Legnth
        text_cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(sql_after_cursor) + len(sql_before_cursor) + right_pad)
        text_cursor.selectedText()
        
        text_edit_sql.setTextCursor(text_cursor)

        return sql[current_position - len(sql_before_cursor):current_position + len(sql_after_cursor) + right_pad].strip()



    def execute(self, result_set_index):
        sql_fragment = self.get_sql_fragment_and_select()

        if sql_fragment:
            cursor = self.connection.cursor()
            cursor.execute(sql_fragment)

            table_model = self.result_sets['result_set_' + str(result_set_index + 1)]

            if cursor.description:
                table_model.headers = [i[0] for i in cursor.description]
                table_model.record_set = cursor.fetchall()
                table_model.update_emit()
                self.f('tab_result_sets').setCurrentIndex(2 + result_set_index)

            text_edit_log = self.f('text_edit_log')
            prefix = '\n' if text_edit_log.toPlainText() else ''
            
            text_edit_log.setText(text_edit_log.toPlainText() + prefix + sql_fragment)
            self.f('text_edit_sql').setFocus()



    def select_tree_object(self, model_index):
        #print(val.row())
        #print(val.column())

        # Isn't a connection
        
        cursor = self.connection.cursor()
        
        
        if model_index.parent().isValid():
            # Is a table
            if model_index.parent().parent().isValid():
                table_name = model_index.data()
                table_name_clean = repr(table_name)[1:-1]
                
                
                cursor.execute("DESCRIBE %s" % table_name_clean)

                self.result_sets['schema'].headers = [i[0] for i in cursor.description]
                self.result_sets['schema'].record_set = cursor.fetchall()
                self.result_sets['schema'].update_emit()
                
                cursor.execute("SELECT * FROM %s LIMIT %d" % (
                    table_name_clean,
                    1000
                ))
                
                self.result_sets['data'].headers = [i[0] for i in cursor.description]
                self.result_sets['data'].record_set = cursor.fetchall()
                self.result_sets['data'].update_emit()
                
                self.f('tab_result_sets').setTabText(0, table_name)
                
            else:
                database_item = self.tree_model.itemFromIndex(model_index)
                #print(val.data())
                #print(val.data())
                #mycursor.execute("USE %s", [val.data()])
                cursor.execute("USE %s" % repr(model_index.data())[1:-1])
                cursor.execute('SHOW TABLES')
                
                #mycursor.execute('SELECT * FROM user WHERE id = %s', tuple('1'))
                #mycursor.execute("USE %s", (val.data()))

                children_count = database_item.rowCount()

                #child = database_item.child(row_num)
                #print(child.text())

                if children_count:
                    for row_num in reversed(range(children_count)):
                        database_item.removeRow(row_num)

                for x in cursor:
                    database_item.appendRow(StandardItem(x[0]))

                self.f('tree_view_objects').expand(model_index)


    def list_databases(self):
        cursor = self.connection.cursor()
        cursor.execute("SHOW DATABASES")

        #treeModel = QStandardItemModel()
        
        root_node = self.tree_model.invisibleRootItem()

        name = '%s:%s' % (
            self.connection.server_host,
            self.connection.server_port
        )
        connection_item = StandardItem(name, 28, set_bold=True)
        root_node.appendRow(connection_item)

        for x in cursor:
            database_item = StandardItem(x[0], 16, set_bold=True)
            connection_item.appendRow(database_item)

        self.f('tree_view_objects').expand(self.tree_model.index(0, 0))


    def connect(self, connection):
        self.connection = connection
        self.list_databases()


    def setup(self):
        self.state = load_state()

        connection_dialog = ConnectionDialog(self)
        self.menu('action_connect', connection_dialog.show)

        self.setup_result_set('result_set_1')
        self.setup_result_set('result_set_2')
        self.setup_result_set('result_set_3')
        self.setup_result_set('data')
        self.setup_result_set('schema')

        #tab_result_sets = self.f('tab_result_sets')

        tree_view_objects = self.f('tree_view_objects')
        self.tree_model = QStandardItemModel()
        tree_view_objects.setModel(self.tree_model)
        #self.list_databases()
        #tree_view_objects.expand(self.tree_model.index(0, 0))
        self.bind(tree_view_objects, 'clicked', self.select_tree_object)

        text_edit_sql = self.f('text_edit_sql')
        self.formatter = syntax_highlighter.create_formatter(text_edit_sql.styleSheet())
        self.query_text_edit_document = QTextDocument(self)
        self.query_text_edit_document.setDefaultStyleSheet(syntax_highlighter.style())
        text_edit_sql.setDocument(self.query_text_edit_document)

        text_edit_log = self.f('text_edit_log')
        self.formatter_log = syntax_highlighter.create_formatter(text_edit_log.styleSheet())
        self.text_edit_log_document = QTextDocument(self)
        self.text_edit_log_document.setDefaultStyleSheet(syntax_highlighter.style())
        text_edit_log.setDocument(self.text_edit_log_document)
        self.is_processing_highlighting = False

        self.bind(text_edit_sql, 'textChanged', self.on_query_changed)
        self.bind('execute_1', 'clicked', lambda: self.execute(0))
        self.f('execute_1').setShortcut('Ctrl+Return')

        self.bind('execute_2', 'clicked', lambda: self.execute(1))

        self.f('execute_2').setShortcut('Ctrl+Enter')
        self.bind('execute_3', 'clicked', lambda: self.execute(2))

        self.bind('table_query', 'currentChanged', self.highlight_log)