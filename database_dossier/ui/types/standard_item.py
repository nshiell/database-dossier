from PyQt5.Qt import QStandardItem
from PyQt5.QtGui import QFont

class StandardItem(QStandardItem):
    #def __init__(self, txt='', font_size=12, set_bold=False, color=QColor(0, 0, 0)):
    def __init__(self, txt='', font_size=12, set_bold=False):
        super().__init__()

        #fnt = QFont('Open Sans', font_size)
        fnt = QFont()
        fnt.setBold(set_bold)

        #self.setEditable(False)
        #self.setForeground(color)
        self.setFont(fnt)
        self.setText(txt)