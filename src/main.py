#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# main.py
#
# Entry point for OctoTray application.
# Depends on 'python-pyqt5'.

import sys
import signal
from PyQt5.QtWidgets import QSystemTrayIcon, QApplication
from OctoTray import OctoTray

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

signal.signal(signal.SIGINT, signal.SIG_DFL)

inSysTray = QSystemTrayIcon.isSystemTrayAvailable()
if ("windowed" in sys.argv) or ("--windowed" in sys.argv) or ("-w" in sys.argv):
    inSysTray = False

tray = OctoTray(app, inSysTray)
rc = app.exec_()

while rc == 42:
    tray.closeAll()
    tray = OctoTray(app, inSysTray)
    rc = app.exec_()

sys.exit(rc)
