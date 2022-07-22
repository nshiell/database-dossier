"""
    Database Dossier - A User Interface for your databases
    Copyright (C) 2022  Nicholas Shiell

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
        self.starting_point_set = False


    def can_undo(self):
        return len(self) > self.position_back + 1


    def can_redo(self):
        return self.position_back > 0


    def add(self, text, position):
        self.append({'text': text, 'position': position})


    def update(self, text, position):
        self[-1] = {'text': text, 'position': position}


    def should_add(self, text, cursor_position):
        if len(self) == 0:
            return True

        last_text = self[-1]['text']
        if not self.starting_point_set and (last_text != text):
            self.starting_point_set = True
            return True

        return text and text[cursor_position - 1] in ' ();\n\t\'"'

        #return len(last_text) and last_text[-1] in ' ();\n\t\'"'


    def truncate_when_updating(self):
        if self.position_back > 0:
            for i in range(0, self.position_back):
                self.pop()
            self.position_back = 0


    def update_state(self, text, cursor_position):
        self.truncate_when_updating()

        if self.should_add(text, cursor_position):
            self.add(text, cursor_position)
        else:
            self.update(text, cursor_position)


    def undo(self):
        self.position_back+= 1


    def redo(self):
        self.position_back-= 1


    @property
    def current(self):
        return self[0 - self.position_back - 1]


class TextDocument(QTextDocument):
    def __init__(self, parent):
        super().__init__(parent)
        self.undo_redoer = UndoRedoerWithCursor()

        # The undo/redo doesn't work if we set HTML content anyway
        self.setUndoRedoEnabled(False)

        # Undoing content actually tries to trigger
        # a new change to the text, hence a new undo state
        # would be created, this flag prevents this
        self.ignore_state_update = False


    def can_undo(self):
        return self.undo_redoer.can_undo()


    def can_redo(self):
        return self.undo_redoer.can_redo()


    @property
    def position(self):
        pass


    @position.setter
    def position(self, position):
        self.update_undo_redoer(position)


    def update_undo_redoer(self, position):
        if not self.ignore_state_update:
            self.undo_redoer.update_state(self.toPlainText(), position)


    def undo(self, cursor=None):
        if self.undo_redoer.can_undo():
            self.ignore_state_update = True
            self.undo_redoer.undo()
            self.setPlainText(self.undo_redoer.current['text'])
            self.ignore_state_update = False
            if cursor:
                cursor.setPosition(self.undo_redoer.current['position'])


    def redo(self, cursor=None):
        if self.undo_redoer.can_redo():
            self.ignore_state_update = True
            self.undo_redoer.redo()
            self.setPlainText(self.undo_redoer.current['text'])
            self.ignore_state_update = False
            if cursor:
                cursor.setPosition(self.undo_redoer.current['position'])


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
