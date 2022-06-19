# for mixin stuff
import os
from pathlib import Path
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class WindowMixin:
    def __init__(self):
        self.xml_root_ = None
        self._artwork_dir = None
        self._extra_ui = None
        self.extra_ui_file_name = None


    def f(self, name):
        return self.findChild(QWidget, name)


    def bind(self, name_or_widget, eventName, callback):
        if isinstance(name_or_widget, QWidget):
            widget = name_or_widget
        else:
            if '.' in name_or_widget:
                parts = name_or_widget.split('.')
                widget_box = self.f(parts[0])
                button = getattr(QDialogButtonBox, parts[1])
                widget = widget_box.button(button)
            else:
                widget = self.f(name_or_widget)
            if widget == None:
                return None
        
        event = getattr(widget, eventName)
        return event.connect(callback)


    # https://stackoverflow.com/questions/9399840/how-to-iterate-through-a-menus-actions-in-qt
    def get_menu_action(self, name, menu=None):
        if menu == None:
            menu = self.menuBar()

        for action in menu.actions():
            if name == action.objectName():
                return action

            submenu = action.menu()
            if submenu:
                if name == submenu.objectName():
                    return submenu

                action_found = self.get_menu_action(name, submenu)
                if action_found:
                    return action_found


    def menu(self, name, callback):
        action = getattr(self, name, None)
        if action:
            return action.triggered.connect(callback)


    def load_xml(self, xml_file):
        # If this file is moved this line will need to change
        ui_dir = str(Path(__file__).resolve().parent.parent)
        self.xml_file = os.path.join(ui_dir, xml_file)

        uic.loadUi(self.xml_file, self)


    @property
    def xml_root(self):
        if not self.xml_root_:
            self.xml_root_ = ET.parse(self.xml_file)

        return self.xml_root_


    def clone_widget_into(self, original, new_widget):
        """ Deep clone the contents of a UI widget into new_widget
            References the original XML file
            that was used to build the UI for source """

        name = original.objectName()
        item = self.xml_root.find('.//widget[@name="%s"]' % name)

        # Not found in the XML DOM?
        if item == None:
            return None
    
        # Get the DOM fragment for the original node as an XML string
        xml_for_clone = str(
            ET.tostring(item, encoding='utf8', method='xml')
        ).replace('\\n', '\n')

        # Strip the XML doctype fromt he top
        without_doctype = xml_for_clone.split('>', 1)[1].replace("'", '')

        # Wrap the fragment in a <ui> tag so that it
        # resembles a UI file in it's own right
        # Also add in a blank <class> tag as sometimes it breaks without it
        wrapped_in_ui_tag = ('<ui version="4.0"><class/>'
            + without_doctype + '</ui>'
        )

        # new_widget will have the temport XML loaded into it
        # as if new_widget was a window
        uic.loadUi(io.StringIO(wrapped_in_ui_tag), new_widget)
    
        return new_widget


    @property
    def artwork_dir(self):
        if not self._artwork_dir:
            path = os.path.realpath(__file__)
            path = os.path.dirname(path) # parent
            path = os.path.dirname(path) # parent
            path = os.path.dirname(path) # parent
            path = os.path.dirname(path) # parent
            self._artwork_dir = os.path.join(path, 'artwork')

        return self._artwork_dir


    @property
    def is_dark(self):
        color = self.palette().color(QPalette.Background)
        average = (color.red() + color.green() + color.blue()) / 3

        return average <= 128


    def set_window_icon_from_artwork(self, file_name):
        self.setWindowIcon(QIcon(os.path.join(self.artwork_dir, file_name)))


    @property
    def extra_ui(self):
        if (self._extra_ui is None):
            class Extra(QMainWindow, WindowMixin): pass
            extra = Extra(self)
            extra.load_xml(self.extra_ui_file_name)
            self._extra_ui = extra

        return self._extra_ui


    def change_style(self, element, changes):
        stylesheet = element.styleSheet()

        if len(stylesheet) and stylesheet[-1] != ';':
            stylesheet+= ';'

        lines = stylesheet.split('\n')

        for (property_name, value, quote) in changes:
            if property_name in stylesheet:
                if quote:
                    value = "'" + value + "'"

                #lines = [x for x in lines if property_name not in x]
                lines_new = []
                for i, line in enumerate(lines):
                    if property_name in line:
                        lines_new.append(property_name + ': ' + value + ';')
                    else:
                        lines_new.append(line)

                lines = lines_new

        element.setStyleSheet('\n'.join(lines))