#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# MainWindow.py
#
# Used when calling application with arguments
# '--windowed' or '-w' on command line,
# or when no system tray is available.

from PyQt5.QtWidgets import QWidget, QVBoxLayout

class MainWindow(QWidget):
    def __init__(self, parent, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.parent = parent

        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.parent.menu)

        self.parent.menu.aboutToHide.connect(self.aboutToHide)

    def aboutToHide(self):
        self.parent.menu.show()

    def closeEvent(self, event):
        self.parent.exit()
        event.accept()
