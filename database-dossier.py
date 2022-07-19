#! /usr/bin/python3
"""
    Blue Log Viewer - Log files in a GUI
    This program is not related to Apache or the Apache Software Foundation in any way
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

import sys, signal
from PyQt5.QtWidgets import QApplication
from database_dossier import MainWindow
from PyQt5 import QtWebEngineWidgets

if __name__ == '__main__':
    # Kill the app on ctrl-c
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    app.exec_()
