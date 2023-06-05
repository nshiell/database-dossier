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

from pygments import highlight as _highlight
from pygments.lexers import SqlLexer
from pygments.formatters import HtmlFormatter


def style():
    style = HtmlFormatter().get_style_defs()
    return style


def create_formatter(stylesheet):
    formatter = HtmlFormatter(cssstyles=stylesheet, style='native')
    formatter.noclasses = True

    return formatter


def highlight(text, formatter):
    extra_char = False
    start_char = False
    if len(text) and text[-1] == "\n":
        extra_char = True
        text+= 'z'

    if len(text) and text[0] == "\n":
        start_char = True
        text = 'a' + text

    # Generated HTML contains unnecessary newline at the end
    # before </pre> closing tag.
    # We need to remove that newline because it's screwing up
    # QTextEdit formatting and is being displayed
    # as a non-editable whitespace.
    # ... but don't trim the input if there was a newline in the origional input

    highlighted = _highlight(text, SqlLexer(), formatter).strip()
    if extra_char:
        highlighted = '</span>'.join(highlighted.rsplit('z</span>', 1))

    if start_char:
        highlighted = '</span>'.join(highlighted.split('a</span>', 1))

    return highlighted