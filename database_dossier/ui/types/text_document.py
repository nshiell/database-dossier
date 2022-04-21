from PyQt5.QtCore import QEvent
from PyQt5.QtGui import *

class TextDocument(QTextDocument):
    def __init__(self, parent):
        super().__init__(parent)

        # The undo/redo doesn't work
        # if we set HTML content anyway
        self.setUndoRedoEnabled(False)

        # Snapshots of the text AND cursor positions
        # Ordered - first is oldest
        self.undo_stack = []

        # How many back steps have we gone though
        self.undo_position_back = 0

        # Undoing content actually tried to trigger
        # a new change to the text, hence a new undo state
        # would be created, this flag prevents this
        self.undo_ignore = False


    def create_text_state(self, text, position):
        return {
            'text': text,
            'position': position
        }


    def undo(self, cursor):
        print('udoing start')
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
        if len(self.undo_stack) == 0:
            return None

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

            # If no text, don't try and store anything
            if len(text):
                last_char_entered = text[position - 1]
                if last_char_entered in ' ();\n\t\'"':
                    self.undo_stack.append(
                        self.create_text_state(text, position)
                    )
                    #print(len(self.undo_stack))


    def get_sql_fragment_start_end_points(self, cursor):
        """
        Looks at where the text cursor is and finds the beginning and end of the
        query, and returns the offset points in the text
        """
        sql = self.toPlainText()

        if not sql.strip():
            return None

        position = cursor.position()

        # Run back the the previous ';' and ahead to the next one
        sql_before_cursor = sql[:position].rsplit(';', 1)[-1].lstrip()
        sql_after_cursor = sql[position:].split(';', 1)[0]

        # Previous was a semi colon, after whitespace
        if self.no_query_under_cursor(sql_before_cursor, sql_after_cursor):
            return None

        sql_before_cursor_length = len(sql_before_cursor)
        sql_after_cursor_length = len(sql_after_cursor)

        # After this substring is a semicolon for the query - include it too
        last_char_pos = position + sql_after_cursor_length
        if sql[last_char_pos : last_char_pos + 1] == ';':
            sql_after_cursor_length+=1

        return (position - sql_before_cursor_length, position + sql_after_cursor_length)


    def no_query_under_cursor(self, sql_before_cursor, sql_after_cursor):
        """
        Situation where we click on the lend of a line after a semi-colon
        Don't try and do anything with the query on the next line
        """

        fist_char_after_cursor_is_whitepsace = (
            len(sql_after_cursor) and sql_after_cursor[0].isspace()
        )

        return (fist_char_after_cursor_is_whitepsace and not sql_before_cursor)
