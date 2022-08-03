import os, json, webbrowser
from PyQt5.QtWidgets import *
from PyQt5.Qt import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from .types import *

class InfoDialog(QDialog, WindowMixin):
    def __init__(self, main_win):
        super().__init__(main_win)
        self._doc_dir = None
        self.setup = False
        self.page = None
        self.document_structure_data = None
        self.last_topic = None
        self.load_ui()


    def load_ui(self):
        self.resize(QSize(600, 300))
        self.load_xml('help.ui')
        self.web_view.page().setBackgroundColor(Qt.transparent)


    def show(self):
        """
        Setting up the URL is expensive
        do it lazily here - rather than on __init__
        """
        if not self.setup:
            self.web_view.setUrl(
                QUrl('file:///' + self.doc_dir.replace('\\', '/') + '/' + self.page)
                #QUrl('file://' + self.doc_dir + '/' + self.page)
            )
            self.document_structure.setModel(QStandardItemModel())
            self.web_view.loadFinished.connect(self.load_finished)
            self.web_view.titleChanged.connect(self.query)
            self.document_structure.clicked.connect(self.tree_click)
            self.setup = True

        super().show()


    def tree_click(self, model_index):
        row = model_index.row()

        lst = self.document_structure_data
        if model_index.parent().isValid():
            lst = lst[model_index.parent().row()]['children']

        if 'name' in lst[row]:
            javascript = "hostClient.event('%s', '%s')" % (
                'topic-scrolled-activated',
                json.dumps(lst[row]['name'])
            )
            self.execute_javascript(javascript)


    def load_finished(self):
        self.execute_javascript('hostClient.implementTitlebarCom()')


    def execute_javascript(self, javascript):
        self.web_view.page().runJavaScript(javascript)


    @pyqtSlot(str)
    def query(self, indexUriData):
        if ':' not in indexUriData:
            return None

        parts = indexUriData.split(':')
        offset = len(parts[0]) + len(parts[1]) + 2
        if parts[1] == 'config-path':
            javascript = "hostClient.response(%d, %s)" % (
                int(parts[0]),
                json.dumps(self.user_config_file_path)
            )
            self.execute_javascript(javascript)
        elif parts[1] == 'document-structure':
            self.document_structure_data = json.loads(indexUriData[offset:])
            model = self.document_structure.model()

            for topic in self.document_structure_data:
                q_topic = QStandardItem(topic['text'])
                for child in topic['children']:
                    q_child = QStandardItem(child['text'])
                    q_topic.appendRow(q_child)
                model.appendRow(q_topic)
        elif parts[1] == 'topic-scrolled-to':
            model = self.document_structure.model()
            selection_model = self.document_structure.selectionModel()
            topic = json.loads(indexUriData[offset:])

            if self.last_topic == topic:
                return None

            selection_model.clearSelection()

            pos = self.get_topic_and_child_pos(topic)
            if pos[0] is None:
                return None

            item = model.item(pos[0])
            self.document_structure.setExpanded(model.indexFromItem(item), True)

            if pos[1] is not None:
                item = item.child(pos[1])

            selection_model.select(
                model.indexFromItem(item),
                selection_model.Select
            )
            self.last_topic = topic
        elif parts[1] == 'is-dark':
            javascript = "hostClient.response(%d, %s)" % (
                int(parts[0]),
                json.dumps(self.parent().is_dark)
            )
            self.execute_javascript(javascript)
        elif parts[1] == 'link':
            webbrowser.get().open_new(json.loads(indexUriData[offset:]))


    def get_topic_and_child_pos(self, name):
        if not self.document_structure_data:
            return (None, None)

        for i, topic in enumerate(self.document_structure_data):
            if topic['name'] == name:
                return (i, None)

            for j, child in enumerate(topic['children']):
                if child['name'] == name:
                    return (i, j)

        return (None, None)


    @property
    def doc_dir(self):
        if not self._doc_dir:
            path = os.path.realpath(__file__)
            path = os.path.dirname(path) # parent
            path = os.path.dirname(path) # parent
            path = os.path.dirname(path) # parent
            self._doc_dir = os.path.join(path, 'doc')

        return self._doc_dir


class HelpDialog(InfoDialog):
    def __init__(self, main_win, user_config_file_path):
        self.user_config_file_path = user_config_file_path
        super().__init__(main_win)
        self.page = 'help.html'


class AboutDialog(InfoDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.page = 'about.html'
        self.setFixedSize(QSize(self.width(), self.height()))
        self.document_structure.hide()


class DonationDialog(InfoDialog):
    def __init__(self, main_win):
        super().__init__(main_win)
        self.page = 'donate.html'
        self.setFixedSize(QSize(self.width(), self.height()))
        self.document_structure.hide()


class ConnectionDialog(QDialog, WindowMixin):
    def __init__(self, main_win):
        super().__init__(main_win)

        self.setFixedSize(QSize(300, 140))
        self.load_xml('connection.ui')

        self.test.clicked.connect(lambda:
            main_win.test_connection(**self.connection_dict)
        )

        self.bind('button_box.Ok', 'clicked', self.add)
        self.bind('button_box.Cancel', 'clicked', self.close)


    def add(self):
        connected = self.parent().add_connection_activate(
            **self.connection_dict
        )

        if connected:
            self.close()


    @property
    def connection_dict(self):
        return {
            'host'     : self.host.text(),
            'port'     : int(self.port.text()),
            'user'     : self.user.text(),
            'password' : self.password.text()
        }


    def show(self):
        self.host.setText('')
        self.port.setValue(3306)
        self.user.setText('')
        self.password.setText('')

        super().show()