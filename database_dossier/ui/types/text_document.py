from PyQt5.QtCore import QEvent
from PyQt5.QtGui import *


class UndoRedoerWithCursor:
    def __init__(self):
        # Snapshots of the text AND cursor positions
        # Ordered - first is oldest
        self.undo_stack = []

        # How many back steps have we gone though
        self.undo_position_back = 0

        # Undoing content actually tried to trigger
        # a new change to the text, hence a new undo state
        # would be created, this flag prevents this
        self.undo_ignore = False


    def add_text_and_position(self, text, position):
        self.undo_stack.append({'text': text, 'position': position})


    def can_undo(self):
        return len(self.undo_stack) > self.undo_position_back


    def can_redo(self):
        return self.undo_position_back > 1


    def undo(self, cursor, text):
        if not self.can_undo():
            return None

        undo_back_position_delta = 1
        should_store_current = (
            self.undo_position_back == 0 and
            self.undo_stack and
            text != self.undo_stack[-1]['text']
        )

        if should_store_current:
            position = cursor.position()
            self.add_text_and_position(text, position)
            undo_back_position_delta+= 1

        self.undo_ignore = True

        new_position_back = self.undo_position_back + undo_back_position_delta

        if len(self.undo_stack) >= new_position_back:
            state = self.undo_stack[0 - new_position_back]
            if state:
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
                return state['text']

        return None


    def redo(self, cursor, text):
        if not self.can_redo():
            return None

        self.undo_ignore = True
        if len(self.undo_stack) == 0:
            return None

        if len(self.undo_stack) > self.undo_position_back - 1:
            state = self.undo_stack[0 - (self.undo_position_back - 1)]
            if state:
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
                return state['text']

        return None


class TextDocument(QTextDocument):
    def __init__(self, parent):
        super().__init__(parent)
        self.undo_redoer = UndoRedoerWithCursor()

        # The undo/redo doesn't work
        # if we set HTML content anyway
        self.setUndoRedoEnabled(False)


    def can_undo(self):
        return self.undo_redoer.can_undo()


    def can_redo(self):
        return self.undo_redoer.can_redo()


    def undo(self, cursor):
        text = self.undo_redoer.undo(cursor, self.toPlainText())

        if text is not None:
            self.setPlainText(text)
            self.undo_redoer.undo_ignore = False


    def redo(self, cursor):
        text = self.undo_redoer.redo(cursor, self.toPlainText())

        if text is not None:
            self.setPlainText(text)
            self.undo_redoer.undo_ignore = False


    def add_to_undo_stack_if_needed(self, cursor):
        if not self.undo_redoer.undo_ignore:
            position = cursor.position()

            text = self.toPlainText()

            # If no text, don't try and store anything
            if len(text):
                last_char_entered = text[position - 1]
                if last_char_entered in ' ();\n\t\'"':
                    self.undo_redoer.add_text_and_position(text, cursor.position())


    def get_sql_fragment_start_end_points(self, cursor):
        """
        Looks at where the text cursor is and finds the beginning and end of the
        query, and returns the offset points in the text
        """
        sql = self.toPlainText()

        if not sql.strip():
            return None

        position = cursor.position()

        return get_sql_fragment_start_end_points(sql, position)

def get_sql_fragment_start_end_points(sql, position):
    # Run back the the previous ';' and ahead to the next one
    (sql_before_cursor, sql_after_cursor) = get_sql_before_and_after(sql, position)

    if should_execute_previous_sql(sql_before_cursor, sql_after_cursor):
        position-= 1
        # Run back before the previous ';' and ahead to the next one
        (sql_before_cursor, sql_after_cursor) = get_sql_before_and_after(sql, position)

    sql_before_cursor_length = len(sql_before_cursor)
    sql_after_cursor_length = len(sql_after_cursor)

    # After this substring is a semicolon for the query - include it too
    last_char_pos = position + sql_after_cursor_length
    if sql[last_char_pos : last_char_pos + 1] == ';':
        sql_after_cursor_length+=1

    return (position - sql_before_cursor_length, position + sql_after_cursor_length)


def get_sql_before_and_after(sql, position):
    return (
        sql[:position].rsplit(';', 1)[-1].lstrip(),
        sql[position:].split(';', 1)[0]
    )


def should_execute_previous_sql(sql_before_cursor, sql_after_cursor):
    # If we actually have some text, before the cursor for this SQL
    # then don't indicate that we should go back
    if sql_before_cursor:
        return False

    # If the next char isn't a newline
    if len(sql_after_cursor) and sql_after_cursor[0] != '\n':
        return False

    return True
