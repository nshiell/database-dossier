from pygments import highlight as _highlight
from pygments.lexers import SqlLexer
from pygments.formatters import HtmlFormatter
from PyQt5.Qt import QObject
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from . import TextDocument

def style():
    style = HtmlFormatter().get_style_defs()
    return style


def create_formatter(stylesheet):
    formatter = HtmlFormatter(cssstyles=stylesheet, style='native')
    formatter.noclasses = True

    return formatter


def highlight(text, formatter):
    extra_char = False
    if len(text) and text[-1] == "\n":
        extra_char = True
        text+= 'z'

    # Generated HTML contains unnecessary newline at the end
    # before </pre> closing tag.
    # We need to remove that newline because it's screwing up
    # QTextEdit formatting and is being displayed
    # as a non-editable whitespace.

    highlighted_text = _highlight(text, SqlLexer(), formatter).strip()

    if extra_char:
        highlighted_text = '</span>'.join(highlighted_text.rsplit('z</span>', 1))

    return highlighted_text


class TextEditor(QObject):
    """
    Ideally this would subclass QTextEdit, but as the element
    is provided by a UI file, that would be tricky
    Instead this class wraps around the QTextEdit

    It applies a custom QDocument to the provied QTextEdit and:
    * Wraps around the document's bespoke undo/redo
    * Makes syntax-highlighing work
    * Implements select SQL fragment
    * Also does the custom context menu implementation
    * And wappers for undo/redo
    """

    def __init__(self, parent, q_text):
        super().__init__(parent)

        self.q_text = q_text
        self.formatter = create_formatter(
            self.q_text.styleSheet()
        )
        self.doc = TextDocument(parent)
        self.q_text.setDocument(self.doc)
        self.is_processing_highlighting = False

        # Built lazy
        self.context_menu = None
        q_text.textChanged.connect(self.query_changed)

        q_text.setContextMenuPolicy(Qt.CustomContextMenu)
        q_text.customContextMenuRequested.connect(self.show_context_menu)
        q_text.installEventFilter(self)


    def show_context_menu(self):
        if self.context_menu is None:
            self.context_menu = QMenu()
            action = QAction(
                QIcon.fromTheme("edit-undo"),
                "&Undo",
                self.q_text
            )

            action.setShortcut('Ctrl+Z')
            action.triggered.connect(self.undo)

            self.context_menu.addAction(action)

            action = QAction(
                QIcon.fromTheme("edit-redo"),
                "&Redo",
                self.q_text
            )

            action.setShortcut('Ctrl+Y')
            action.triggered.connect(self.redo)

            self.context_menu.addAction(action)

        self.context_menu.exec_(QCursor.pos())


    def undo(self):
        self.doc.undo(self.q_text.textCursor())


    def redo(self):
        self.doc.redo(self.q_text.textCursor())


    def query_changed(self):
        """Process query edits by user"""
        if self.is_processing_highlighting:
            # If we caused the invokation of this slot by set highlighted
            # HTML text into query editor, then ignore this call and
            # mark highlighting processing as finished.
            self.is_processing_highlighting = False
            return None

        # If changes to text were made by user, mark beginning of
        # highlighting process
        self.is_processing_highlighting = True

        # Get plain text query and highlight it

        # After we set highlighted HTML back to QTextEdit form
        # the cursor will jump to the end of the text.
        # To avoid that we remember the current position of the cursor.
        cursor = self.q_text.textCursor()
        self.doc.add_to_undo_stack_if_needed(cursor)

        position = cursor.position()
        # Set highlighted text back to editor which will cause the
        # cursor to jump to the end of the text.

        text = self.q_text.toPlainText()

        # Setting the cursor pos on whitepsace
        # only strings causes problems
        if text.strip():
            self.doc.setHtml(highlight(text, self.formatter))

            # Return cursor back to the old position
            cursor.setPosition(position)
            self.q_text.setTextCursor(cursor)


    def eventFilter(self, obj, event):
        #print('obj.objectName()')
        if event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Undo):
                print('undo triggered')
                self.undo()
                return True
            if event.matches(QKeySequence.Redo):
                print('redo triggered')
                self.redo()
                return True

        return super().eventFilter(obj, event)
