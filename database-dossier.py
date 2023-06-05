#!/usr/bin/env python3
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
"""

import sys, signal
from PyQt5.QtWidgets import QApplication
from database_dossier import MainWindow
from database_dossier.ui.types.window_mixin import load_web_engine_if_needed

if __name__ == '__main__':
    # Kill the app on ctrl-c
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    load_web_engine_if_needed()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    app.exec_()
