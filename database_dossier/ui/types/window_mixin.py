# for mixin stuff
from pathlib import Path
from PyQt5 import uic
from PyQt5.QtWidgets import *

class WindowMixin:
    def __init__(self):
        self.xml_root_ = None


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
                action_found = self.get_menu_action(name, submenu)
                if action_found:
                    return action_found


    def menu(self, name, callback):
        return self.get_menu_action(name).triggered.connect(callback)


    def load_xml(self, xml_file):
        # If this file is moved this line will need to change
        ui_dir = str(Path(__file__).resolve().parent.parent) + '/'
        self.xml_file = ui_dir + xml_file

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