from PyQt5.QtCore import QEvent
from PyQt5.QtGui import *


class UndoRedoerWithCursor(list):
    """
    Snapshots of the text AND cursor positions
    Ordered - first is oldest
    """
    def __init__(self):
        # How many back steps have we gone though
        self.position_back = 0

        # Undoing content actually tried to trigger
        # a new change to the text, hence a new undo state
        # would be created, this flag prevents this
        self.undo_ignore = False


    def add_text_and_position(self, text, position):
        self.append({'text': text, 'position': position})


    def can_undo(self):
        return len(self) > self.position_back


    def can_redo(self):
        return self.position_back > 1


    def apply_state(self, cursor, new_undo_position_back):
        state = self[0 - new_undo_position_back]

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

        self.position_back = new_undo_position_back


    def should_store_current_text(self, text):
        if self.position_back != 0:
            return False

        if len(self) == 0:
            return False

        if text == self[-1]['text']:
            return False

        return True


    def undo(self, cursor, text):
        if not self.can_undo():
            return None

        undo_back_position_delta = 1

        if self.should_store_current_text(text):
            position = cursor.position()
            self.add_text_and_position(text, position)
            undo_back_position_delta = 2

        new_position_back = self.position_back + undo_back_position_delta

        if len(self) >= new_position_back:
            self.undo_ignore = True
            self.apply_state(cursor, new_position_back)
            return self[0 - new_position_back]['text']

        return None


    def redo(self, cursor, text):
        if not self.can_redo():
            return None

        if len(self) == 0:
            return None

        new_position_back = self.position_back - 1

        if len(self) > new_position_back:
            self.undo_ignore = True
            self.apply_state(cursor, new_position_back)
            return self[0 - new_position_back]['text']

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
    (sql_before, sql_after) = get_sql_before_and_after(sql, position)

    if should_execute_previous_sql(sql_before, sql_after):
        position-= 1
        # Run back before the previous ';' and ahead to the next one
        (sql_before, sql_after) = get_sql_before_and_after(sql, position)

    sql_before_length = len(sql_before)
    sql_after_length = len(sql_after)

    # After this substring is a semicolon for the query - include it too
    last_char_pos = position + sql_after_length
    if sql[last_char_pos : last_char_pos + 1] == ';':
        sql_after_length+=1

    return (position - sql_before_length, position + sql_after_length)


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
