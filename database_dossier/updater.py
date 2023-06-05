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

from datetime import datetime
from PyQt5.QtWidgets import *


past_date = datetime(2023, 6, 1)
months_to_live = 6
age_months = ((datetime.now() - past_date).days) / 30


def show_please_update():
    if age_months > months_to_live:
        box = QMessageBox()
        box.setIcon(QMessageBox.Information)

        box.setText(
            "This version of Database Dossier is getting a bit old."
            + '\n'
            + 'It is ' + str(int(age_months)) + ' months old!'
            + '\n'
            + "Why not see if there is newer version?"
        )
        box.setWindowTitle("Database Dossier")
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()