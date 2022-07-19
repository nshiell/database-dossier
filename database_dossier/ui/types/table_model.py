from numbers import Number
from datetime import datetime, date
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QColor

class TableModel(QAbstractTableModel):
    def __init__(self, record_set_colors):
        self.headers = None
        self.record_set = None
        self.is_error = False
        self.record_set_colors = record_set_colors
        super().__init__()
    
    
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if self.headers:
                return self.headers[col]

        return None

    def rowCount(self, parent):
        if self.record_set:
            return len(self.record_set)

        return 0

    def columnCount(self, parent):
        if self.headers:
            return len(self.headers)

        return 0

    def update_emit(self):
        self.layoutChanged.emit()

    def data(self, index, role):
        if not index.isValid():
            return None

        text = self.record_set[index.row()][index.column()]
        if role == Qt.TextColorRole:
            if self.is_error:
                return self.record_set_colors['error']
            if isinstance(text, datetime) or isinstance(text, date):
                return self.record_set_colors['date']
            if isinstance(text, Number):
                return self.record_set_colors['number']

        elif role == Qt.TextAlignmentRole:
            right =  (
                isinstance(text, datetime) or
                isinstance(text, date) or
                isinstance(text, Number)
            )

            if right:
                return QVariant(Qt.AlignRight | Qt.AlignVCenter)

        elif role == Qt.DisplayRole:
            if isinstance(text, (bytes, bytearray)):
                text = text.decode("utf-8")

            return str(text)
