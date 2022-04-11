from PyQt5.QtGui import *

class TextDocument(QTextDocument):
    def __init__(self, parent):
        super().__init__(parent)

        self.undo_stack = []
        self.undo_position_back = 0
        self.undo_ignore = False


    def create_text_state(self, text, position):
        return {
            'text': text,
            'position': position
        }


    def undo(self, cursor):
        undo_back_position_delta = 1
        text = self.toPlainText()
        should_store_current = (
            self.undo_position_back == 0 and
            self.undo_stack and
            text != self.undo_stack[-1]['text']
        )

        if should_store_current:
            position = cursor.position()
            self.undo_stack.append(
                self.create_text_state(text, position)
            )
            undo_back_position_delta+= 1

        self.undo_ignore = True

        new_position_back = self.undo_position_back + undo_back_position_delta

        if len(self.undo_stack) > new_position_back:
            state = self.undo_stack[0 - new_position_back]
            if state:
                self.setPlainText(state['text'])
                cursor.clearSelection()
                cursor.movePosition(
                    QTextCursor.Start,
                    QTextCursor.MoveAnchor
                )

                cursor.movePosition(
                    QTextCursor.Right,
                    QTextCursor.MoveAnchor,
                    state['position']
                )

                self.undo_position_back = new_position_back
                self.undo_ignore = False


    def redo(self, cursor):
        self.undo_ignore = True
        if len(self.undo_stack) > self.undo_position_back - 1:
            state = self.undo_stack[0 - (self.undo_position_back - 1)]
            if state:
                text = self.toPlainText()
                self.setPlainText(state['text'])
                cursor.clearSelection()
                cursor.movePosition(
                    QTextCursor.Start,
                    QTextCursor.MoveAnchor
                )

                cursor.movePosition(
                    QTextCursor.Right,
                    QTextCursor.MoveAnchor,
                    state['position']
                )

                self.undo_position_back-= 1
                self.undo_ignore = False


    def add_to_undo_stack_if_needed(self, cursor):
        if not self.undo_ignore:
            position = cursor.position()

            text = self.toPlainText()
            if len(text) >= position:
                last_char_entered = text[position - 1]
                if last_char_entered in ' ();\n\t\'"':
                    self.undo_stack.append(
                        self.create_text_state(text, position)
                    )