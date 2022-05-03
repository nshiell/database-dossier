import csv
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
    formatter = HtmlFormatter(style='native', prestyles=stylesheet)
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

    def __init__(self, parent, q_text, **kwargs):
        super().__init__(parent)
        self.options = kwargs
        self.q_text = q_text
        self.formatter = create_formatter(self.q_text.styleSheet())
        self.doc = TextDocument(parent)
        self.q_text.setDocument(self.doc)
        self.is_processing_highlighting = False

        self.context_menu_actions = {}
        self.setup_menu()
        q_text.textChanged.connect(self.query_changed)
        q_text.setContextMenuPolicy(Qt.CustomContextMenu)
        q_text.customContextMenuRequested.connect(lambda:
            kwargs['context_menu'].exec_(QCursor.pos())
        )
        q_text.installEventFilter(self)


    @property
    def plain_text(self):
        return self.q_text.toPlainText()

    @plain_text.setter
    def plain_text(self, text):
        self.q_text.setPlainText(text)
        self.doc.position = self.q_text.textCursor().position()


    def font_point_size_increase(self):
        if self.font_point_size < 90:
            self.font_point_size+= 1


    def font_point_size_decrease(self):
        if self.font_point_size > 4:
            self.font_point_size-= 1


    @property
    def font(self):
        return QFont(
            self.font_name,
            pointSize=self.font_point_size,
            italic=False,
            weight=1
        )


    @font.setter
    def font(self, font):
        self.set_stylesheet_property([
            ('font-size', str(font.pointSize()) + 'pt', False),
            ('font-family', font.family(), True),
            (
                'font-weight',
                'bold' if font.weight() > 50 else 'normal',
                False
            ),
            (
                'font-style',
                'italic' if font.italic() else 'normal',
                False
            )
        ])


    @property
    def font_bold(self):
        stylesheet = self.q_text.styleSheet()
        if 'font-weight' not in stylesheet:
            return False

        value = (stylesheet.split('font-weight')[1]
            .split(':')[1].split(';')[0].strip()
        )
        return value == 'bold'


    @property
    def font_italic(self):
        stylesheet = self.q_text.styleSheet()
        if 'font-style' not in stylesheet:
            return False

        value = (stylesheet.split('font-style')[1]
            .split(':')[1].split(';')[0].strip()
        )
        return value == 'italic'


    @property
    def font_point_size(self):
        stylesheet = self.q_text.styleSheet()
        if 'font-size' not in stylesheet:
            return None

        return int(
            stylesheet.split('font-size')[1].split(':')[1].split(';')[0].strip()[:-2]
        )


    @font_point_size.setter
    def font_point_size(self, size):
        self.set_stylesheet_property([('font-size', str(size) + 'pt', False)])


    @property
    def font_name(self):
        stylesheet = self.q_text.styleSheet()
        if 'font-family' not in stylesheet:
            return None

        font_line = stylesheet.split('font-family')[1].split(';')[0]
        fonts = font_line.replace(':', '').replace("'", '"').strip()

        font_list = list(csv.reader([fonts],
            skipinitialspace=True,
            delimiter=',',
            quotechar='"'
        ))[0]


        available_fonts = QFontDatabase().families()
        for font in font_list:
            if font in available_fonts:
                return font

        return None


    @font_name.setter
    def font_name(self, font_name):
        self.set_stylesheet_property([('font-family', font_name, True)])


    def set_stylesheet_property(self, changes):
        stylesheet = self.q_text.styleSheet()

        if len(stylesheet) and stylesheet[-1] != ';':
            stylesheet+= ';'

        lines = stylesheet.split('\n')

        for (property_name, value, quote) in changes:
            if property_name in stylesheet:
                lines = [x for x in lines if property_name not in x]
    
            if quote:
                value = "'" + value + "'"
    
            lines.append(property_name + ': ' + value + ';')

        stylesheet = '\n'.join(lines)
        self.q_text.setStyleSheet(stylesheet)
        self.formatter = create_formatter(stylesheet)
        self.query_changed()



    def setup_menu(self):
        self.context_menu = QMenu()
        action = QAction(
            QIcon.fromTheme("edit-undo"),
            "&Undo",
            self.q_text
        )

        action.setShortcut('Ctrl+Z')
        action.triggered.connect(self.undo)
        self.context_menu_actions['undo'] = action
        self.context_menu.addAction(action)

        action = QAction(
            QIcon.fromTheme("edit-redo"),
            "&Redo",
            self.q_text
        )

        action.setShortcut('Ctrl+Y')
        action.triggered.connect(self.redo)
        self.context_menu_actions['redo'] = action
        self.context_menu.addAction(action)


    def undo(self):
        cursor = self.q_text.textCursor()
        self.doc.undo(cursor)
        self.q_text.setTextCursor(cursor)


    def redo(self):
        cursor = self.q_text.textCursor()
        self.doc.redo(cursor)
        self.q_text.setTextCursor(cursor)


    def update_undo_redo_menus(self):
        if 'update_cb' in self.options:
            self.options['update_cb'](self.doc.can_undo(), self.doc.can_redo())


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
        position = cursor.position()
        # Set highlighted text back to editor which will cause the
        # cursor to jump to the end of the text.

        self.doc.position = cursor.position()

        text = self.q_text.toPlainText()

        # Setting the cursor pos on whitepsace
        # only strings causes problems
        if text.strip():
            self.doc.setHtml(highlight(text, self.formatter))

            # Return cursor back to the old position
            cursor.setPosition(position)
            self.q_text.setTextCursor(cursor)

        self.update_undo_redo_menus()


    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Undo):
                self.undo()
                return True

            if event.matches(QKeySequence.Redo):
                self.redo()
                return True

        return super().eventFilter(obj, event)
