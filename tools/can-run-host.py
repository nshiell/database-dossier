#! /usr/bin/python3

import sys

try:
    from PyQt5 import QtWidgets
except ImportError:
    print('FAIL')
    sys.exit()

try:
    from PyQt5.QtWebKitWidgets import QWebView
except ImportError:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        print('FAIL')
        sys.exit()

print('ALL_OK')
