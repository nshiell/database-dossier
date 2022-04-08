from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QColor

class TableModel(QAbstractTableModel):
    def __init__(self, *args):
        self.headers = None
        self.record_set = None
        self.is_error = False
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

        if role == Qt.TextColorRole and self.is_error:
            return QVariant(QColor(Qt.red))

        if role == Qt.DisplayRole:
            text = self.record_set[index.row()][index.column()]
            if isinstance(text, (bytes, bytearray)):
                text = text.decode("utf-8") 

            return text
