from PyQt5.QtWidgets import *

# for mixin stuff
from pathlib import Path
from PyQt5 import uic

import mysql.connector

from .ui import *

#from PyQt5.Qt import QStandardItemModel, QStandardItem, QTextDocument
from PyQt5.Qt import QStandardItemModel, QTextDocument
from PyQt5.QtGui import QTextCursor, QIcon
from PyQt5.QtCore import *
from . import syntax_highlighter


from .store import *

class WindowMixin:
    def __init__(self):
        self.xml_root_ = None


    def f(self, name):
        return self.findChild(QWidget, name)


    def bind(self, name_or_widget, eventName, callback):
        if isinstance(name_or_widget, QWidget):
            widget = name_or_widget
        else:
            if '.' in name_or_widget:
                parts = name_or_widget.split('.')
                widget_box = self.f(parts[0])
                button = getattr(QDialogButtonBox, parts[1])
                widget = widget_box.button(button)
            else:
                widget = self.f(name_or_widget)
            if widget == None:
                return None
        
        event = getattr(widget, eventName)
        return event.connect(callback)


    # https://stackoverflow.com/questions/9399840/how-to-iterate-through-a-menus-actions-in-qt
    def get_menu_action(self, name, menu=None):
        if menu == None:
            menu = self.menuBar()

        for action in menu.actions():
            if name == action.objectName():
                return action

            submenu = action.menu()
            if submenu:
                action_found = self.get_menu_action(name, submenu)
                if action_found:
                    return action_found


    def menu(self, name, callback):
        return self.get_menu_action(name).triggered.connect(callback)


    def load_xml(self, xml_file):
        # If this file is moved this line will need to change
        #ui_dir = str(Path(__file__).resolve().parent.parent) + '/ui/'
        ui_dir = str(Path(__file__).resolve().parent) + '/ui/'
        self.xml_file = ui_dir + xml_file

        uic.loadUi(self.xml_file, self)


    @property
    def xml_root(self):
        if not self.xml_root_:
            self.xml_root_ = ET.parse(self.xml_file)

        return self.xml_root_


    def clone_widget_into(self, original, new_widget):
        """ Deep clone the contents of a UI widget into new_widget
            References the original XML file
            that was used to build the UI for source """

        name = original.objectName()
        item = self.xml_root.find('.//widget[@name="%s"]' % name)

        # Not found in the XML DOM?
        if item == None:
            return None
    
        # Get the DOM fragment for the original node as an XML string
        xml_for_clone = str(
            ET.tostring(item, encoding='utf8', method='xml')
        ).replace('\\n', '\n')

        # Strip the XML doctype fromt he top
        without_doctype = xml_for_clone.split('>', 1)[1].replace("'", '')

        # Wrap the fragment in a <ui> tag so that it
        # resembles a UI file in it's own right
        # Also add in a blank <class> tag as sometimes it breaks without it
        wrapped_in_ui_tag = ('<ui version="4.0"><class/>'
            + without_doctype + '</ui>'
        )

        # new_widget will have the temport XML loaded into it
        # as if new_widget was a window
        uic.loadUi(io.StringIO(wrapped_in_ui_tag), new_widget)
    
        return new_widget



def create_connection(host, user, password, port):
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="sdfgSFGsa3452345sdfg456346",
        #password='apple',
        auth_plugin='mysql_native_password',
        port=3307,
        autocommit=True
        #port=3306
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
        print(self.size())
        
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
                print(self.parent().connect(connection))
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
        
        self.menu('action_connect', lambda:
            ConnectionDialog(self).show()
        )


    def connect(self, connection):
        """mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="sdfgSFGsa3452345sdfg456346",
            #password='apple',
            auth_plugin='mysql_native_password',
            port=3307,
            autocommit=True
            #port=3306
        )"""
        
        mycursor = connection.cursor()
        
        
        self.connection = connection
        
        #self.cursor = mycursor
        
        
        mycursor.execute("SHOW DATABASES")

        treeModel = QStandardItemModel()
        rootNode = treeModel.invisibleRootItem()

        connection = StandardItem('localhost:3307', 16, set_bold=True)
        rootNode.appendRow(connection)




        self.table_model_result_set_1 = TableModel()
        table_view_result_set_1 = self.f('table_view_result_set_1')
        table_view_result_set_1.setModel(self.table_model_result_set_1)
        
        table_view_result_set_1.setContextMenuPolicy(Qt.CustomContextMenu)
        def context_menu(point):
            index = table_view_result_set_1.indexAt(point)
            menu = QMenu(self)
            action1 = QAction(QIcon("edit-copy"), "&Copy")
            action1.triggered.connect(lambda:
                app.clipboard().setText(index.data())
            )

            menu.addAction(action1)
            menu.exec_(QCursor.pos())

        table_view_result_set_1.customContextMenuRequested.connect(context_menu)
        
        

        self.table_model_result_set_2 = TableModel()
        table_view_result_set_2 = self.f('table_view_result_set_2')
        table_view_result_set_2.setModel(self.table_model_result_set_2)

        table_view_result_set_2.setContextMenuPolicy(Qt.CustomContextMenu)
        def context_menu(point):
            index = table_view_result_set_2.indexAt(point)
            menu = QMenu(self)
            action1 = QAction(QIcon("edit-copy"), "&Copy")
            action1.triggered.connect(lambda:
                app.clipboard().setText(index.data())
            )

            menu.addAction(action1)
            menu.exec_(QCursor.pos())

        table_view_result_set_2.customContextMenuRequested.connect(context_menu)





        self.table_model_result_set_3 = TableModel()
        table_view_result_set_3 = self.f('table_view_result_set_3')
        table_view_result_set_3.setModel(self.table_model_result_set_3)

        table_view_result_set_3.setContextMenuPolicy(Qt.CustomContextMenu)
        def context_menu(point):
            index = table_view_result_set_3.indexAt(point)
            menu = QMenu(self)
            action1 = QAction(QIcon("edit-copy"), "&Copy")
            action1.triggered.connect(lambda:
                app.clipboard().setText(index.data())
            )

            menu.addAction(action1)
            menu.exec_(QCursor.pos())

        table_view_result_set_3.customContextMenuRequested.connect(context_menu)


        self.table_model_data = TableModel()

        table_view_data = self.f('table_view_data')
        table_view_data.setModel(self.table_model_data)
        table_view_data.setContextMenuPolicy(Qt.CustomContextMenu)
        def context_menu(point):
            index = table_view_data.indexAt(point)
            menu = QMenu(self)
            action1 = QAction(QIcon("edit-copy"), "&Copy")
            action1.triggered.connect(lambda:
                app.clipboard().setText(index.data())
            )

            menu.addAction(action1)
            menu.exec_(QCursor.pos())

        table_view_data.customContextMenuRequested.connect(context_menu)


        
        self.table_model_schema = TableModel()

        table_view_schema = self.f('table_view_schema')
        table_view_schema.setModel(self.table_model_schema)




        table_view_schema.setContextMenuPolicy(Qt.CustomContextMenu)
        def context_menu(point):
            index = table_view_schema.indexAt(point)
            menu = QMenu(self)
            action1 = QAction(QIcon("edit-copy"), "&Copy")
            action1.triggered.connect(lambda:
                app.clipboard().setText(index.data())
            )

            menu.addAction(action1)
            menu.exec_(QCursor.pos())

        table_view_schema.customContextMenuRequested.connect(context_menu)






        tab_result_sets = self.f('tab_result_sets')


        for x in mycursor:
            database = StandardItem(x[0], 16, set_bold=True)
            connection.appendRow(database)
            #connection.setExpanded(1)

        
        
        #america = StandardItem('America', 16, set_bold=True)

        #rootNode.appendRow(america)

        tree_view_objects = self.f('tree_view_objects')

        def getValue(model_index):
            #print(val.row())
            #print(val.column())


            # Isn't a connection
            if model_index.parent().isValid():
                # Is a table
                if model_index.parent().parent().isValid():
                    table_name = model_index.data()
                    table_name_clean = repr(table_name)[1:-1]
                    
                    
                    mycursor.execute("DESCRIBE %s" % table_name_clean)

                    self.table_model_schema.headers = [i[0] for i in mycursor.description]
                    self.table_model_schema.record_set = mycursor.fetchall()
                    
                    self.table_model_schema.update_emit()
                    
                    mycursor.execute("SELECT * FROM %s LIMIT %d" % (
                        table_name_clean,
                        1000
                    ))
                    
                    self.table_model_data.headers = [i[0] for i in mycursor.description]
                    self.table_model_data.record_set = mycursor.fetchall()
                    self.table_model_data.update_emit()
                    
                    tab_result_sets.setTabText(0, table_name)
                    
                else:
                    database_item = treeModel.itemFromIndex(model_index)
                    #print(val.data())
                    #print(val.data())
                    #mycursor.execute("USE %s", [val.data()])
                    mycursor.execute("USE %s" % repr(model_index.data())[1:-1])
                    mycursor.execute('SHOW TABLES')
                    
                    #mycursor.execute('SELECT * FROM user WHERE id = %s', tuple('1'))
                    #mycursor.execute("USE %s", (val.data()))

                    children_count = database_item.rowCount()
    
                    #child = database_item.child(row_num)
                    #print(child.text())
    
                    if children_count:
                        for row_num in reversed(range(children_count)):
                            database_item.removeRow(row_num)
    
                    for x in mycursor:
                        database_item.appendRow(StandardItem(x[0]))
    
                    tree_view_objects.expand(model_index)

        tree_view_objects.setModel(treeModel)
        index = treeModel.index(0, 0)
        tree_view_objects.expand(index)
        
        
        self.bind(tree_view_objects, 'clicked', getValue)

        query_text_edit_document = QTextDocument(self)
        query_text_edit_document.setDefaultStyleSheet(syntax_highlighter.style())
        text_edit_sql = self.f('text_edit_sql')
        
        
        
        
        text_edit_log = self.f('text_edit_log')
        
        
        text_edit_log_document = QTextDocument(self)
        text_edit_log_document.setDefaultStyleSheet(syntax_highlighter.style())
        text_edit_log.setDocument(text_edit_log_document)


        self.is_processing_highlighting = False
        #self.formatter = syntax_highlighter.create_formatter(text_edit_sql.styleSheet())
        self.formatter = syntax_highlighter.create_formatter(text_edit_sql.styleSheet())
        self.formatter_log = syntax_highlighter.create_formatter(text_edit_log.styleSheet())
        
        def on_query_changed():
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
                # Get plain text query and highlight it
    
                # After we set highlighted HTML back to QTextEdit form
                # the cursor will jump to the end of the text.
                # To avoid that we remember the current position of the cursor.
                current_cursor = text_edit_sql.textCursor()
                current_cursor_position = current_cursor.position()
                # Set highlighted text back to editor which will cause the
                # cursor to jump to the end of the text.

                #highlighted_query_text = highlighted_query_text.replace('z</span>', '</span>')

                query_text_edit_document.setHtml(
                    syntax_highlighter.highlight(
                        text_edit_sql.toPlainText(),
                        self.formatter
                    )
                )
                #print(highlighted_query_text)
                # Return cursor back to the old position
                current_cursor.setPosition(current_cursor_position)
                text_edit_sql.setTextCursor(current_cursor)

        text_edit_sql.setDocument(query_text_edit_document)
        self.bind(text_edit_sql, 'textChanged', on_query_changed)


        def get_sql_fragment_and_select():
            sql = text_edit_sql.toPlainText()

            if not sql.strip():
                return None

            cursor = text_edit_sql.textCursor()
            selected_text = cursor.selectedText()
            
            if selected_text:
                return selected_text
            
            
            current_position = cursor.position()

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
            
            cursor.clearSelection()
            
            cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
            # last char
            cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, current_position + len(sql_after_cursor) + right_pad)
            #Legnth
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(sql_after_cursor) + len(sql_before_cursor) + right_pad)
            cursor.selectedText()
            
            text_edit_sql.setTextCursor(cursor)

            return sql[current_position - len(sql_before_cursor):current_position + len(sql_after_cursor) + right_pad].strip()

        def execute(mycursor, result_set_index):

            sql_fragment = get_sql_fragment_and_select()

            if sql_fragment:
                mycursor = self.connection.cursor()
                
                #print(current_cursor)
                #mycursor = self.cursor
                mycursor.execute(sql_fragment)
    
                if result_set_index == 0:
                    table_model = self.table_model_result_set_1
                elif result_set_index == 1:
                    table_model = self.table_model_result_set_2
                elif result_set_index == 2:
                    table_model = self.table_model_result_set_3
    
                if mycursor.description:
                    table_model.headers = [i[0] for i in mycursor.description]
                    table_model.record_set = mycursor.fetchall()
                    table_model.update_emit()
                    tab_result_sets.setCurrentIndex(2 + result_set_index)
    
                prefix = '\n' if text_edit_log.toPlainText() else ''
                text_edit_log.setText(text_edit_log.toPlainText() + prefix + sql_fragment)
                text_edit_sql.setFocus()

        self.bind('execute_1', 'clicked', lambda: execute(mycursor, 0))
        self.f('execute_1').setShortcut('Ctrl+Return')
        self.bind('execute_2', 'clicked', lambda: execute(mycursor, 1))
        self.f('execute_2').setShortcut('Ctrl+Enter')
        self.bind('execute_3', 'clicked', lambda: execute(mycursor, 2))
        
        
        def highlight_log(new_index):
            if new_index == 1:
                text_edit_log_document.setHtml(
                syntax_highlighter.highlight(
                    text_edit_log.toPlainText(),
                    self.formatter_log
                )
            )
        
        self.bind('table_query', 'currentChanged', highlight_log)