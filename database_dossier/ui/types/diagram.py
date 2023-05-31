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

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import os
import json

class Diagram(QObject):
    def __init__(self, q_webview):
        super().__init__()
        self.hover_table = None
        self._doc_dir = None
        self._schema = None
        self.event_bindings = {}
        self.q_webview = q_webview
        self.q_webview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.q_webview.customContextMenuRequested.connect(self.context_menu_table)

        q_webview.setUrl(
            QUrl('file:///' + self.doc_dir.replace('\\', '/') + '/diagram.html')
        )


    def context_menu_table(self):
        if self.hover_table:
            self.trigger('context_menu_table', (
                QCursor.pos(),
                self.hover_table
            ))


    def trigger(self, event_name, args=None):
        if event_name in self.event_bindings:
            for binding in self.event_bindings[event_name]:
                if args is None:
                    binding()
                else:
                    binding(*args)


    def bind(self, event_name, event_callback):
        if event_name not in self.event_bindings:
            self.event_bindings[event_name] = []

        self.event_bindings[event_name].append(event_callback)


    def setup(self):
        self.q_webview.loadFinished.connect(self.load_finished)
        self.q_webview.titleChanged.connect(self.query)


    def load_finished(self):
        #self.execute_javascript('hostClient.implementTitlebarCom()')
        self.q_webview.page().mainFrame().addToJavaScriptWindowObject('host', self)
        self.execute_javascript('hostClient.implementHostCom()')


    def execute_javascript(self, javascript):
        #self.web_view.page().runJavaScript(javascript)
        self.q_webview.page().mainFrame().evaluateJavaScript(javascript)

    @property
    def schema(self):
        return self._schema

    @schema.setter
    def schema(self, schema):
        self._schema = schema
        javascript = "hostClient.event('%s', '%s')" % (
            'schema-new',
            json.dumps(schema)
        )
        self.execute_javascript(javascript)


    @pyqtSlot(str)
    def query(self, indexUriData):
        if ':' not in indexUriData:
            return None

        parts = indexUriData.split(':')
        offset = len(parts[0]) + len(parts[1]) + 2
        if parts[1] == 'schema':
            javascript = "hostClient.response(%d, %s)" % (
                int(parts[0]),
                json.dumps(self.schema)
            )
            self.execute_javascript(javascript)

        elif parts[1] == 'selected':
            self.trigger('selected', [json.loads(parts[2])])

        elif parts[1] == 'hover_table_set':
            self.hover_table = json.loads(parts[2])

        elif parts[1] == 'hover_table_clear':
            self.hover_table = None

#border_color = self.palette().color(QPalette.Link).name()

    @property
    def doc_dir(self):
        if not self._doc_dir:
            path = os.path.realpath(__file__)
            path = os.path.dirname(path) # parent
            path = os.path.dirname(path) # parent
            path = os.path.dirname(path) # parent
            path = os.path.dirname(path) # parent
            self._doc_dir = os.path.join(path, 'diagram')

        return self._doc_dir