"""
    Database Dossier - A User Interface for your databases
    Copyright (C) 2023  Nicholas Shiell

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


def load_web_engine_if_needed():
    try:
        from PyQt5.QtWebKitWidgets import QWebView
        return False
    except:
        from PyQt5 import QtWebEngineWidgets
        return True


class Diagram(QObject):
    def __init__(self, q_webview):
        super().__init__()
        self.hover_table = None
        self._doc_dir = None
        self._schema = None
        self.page_colors = {}
        self.colors = {}
        self.event_bindings = {}
        self.position_overrides = {}
        self.q_webview = q_webview
        self.q_webview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.q_webview.customContextMenuRequested.connect(self.context_menu_table)
        QApplication.instance().focusChanged.connect(self.focusChanged)
        q_webview.setUrl(
            QUrl('file:///' + self.doc_dir.replace('\\', '/') + '/diagram.html')
        )


    def focusChanged(self, new, old):
        if old == self.q_webview:
            self.execute_javascript("hostClient.event('blur', null)")
        elif new == self.q_webview:
            self.execute_javascript("hostClient.event('focus', null)")



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
        if load_web_engine_if_needed():
            self.execute_javascript('hostClient.implementTitlebarCom()')
        else:
            self.q_webview.page().mainFrame().addToJavaScriptWindowObject('host', self)
            self.execute_javascript('hostClient.implementHostCom()')


    def execute_javascript(self, javascript):
        if load_web_engine_if_needed():
            self.q_webview.page().runJavaScript(javascript)
        else:
            self.q_webview.page().mainFrame().evaluateJavaScript(javascript)


    @property
    def schema(self):
        return self._schema


    @schema.setter
    def schema(self, schema):
        self._schema = schema
        javascript = "hostClient.event('%s', '%s')" % (
            'schema-new',
            json.dumps({
                'schema': self.schema,
                'pos': self.position_overrides,
                'colors': self.colors
            })
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
                json.dumps({
                    'schema': self.schema,
                    'pos': self.position_overrides,
                    'colors': self.colors
                })
            )
            self.execute_javascript(javascript)

        if parts[1] == 'page_colors':
            page_colors = self.page_colors
            page_colors['web_engine'] = load_web_engine_if_needed()
            javascript = "hostClient.response(%d, %s)" % (
                int(parts[0]),
                json.dumps(page_colors)
            )
            self.execute_javascript(javascript)

        elif parts[1] == 'selected':
            self.trigger('selected', [json.loads(parts[2])])

        elif parts[1] == 'hover_table_set':
            self.hover_table = json.loads(parts[2])

        elif parts[1] == 'hover_table_clear':
            self.hover_table = None

        elif parts[1] == 'store_state':
            self.trigger('state_change', [json.loads(indexUriData[offset:])])


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