#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# SettingsWindow.py
#
# UI for changes to application configuration.

import string
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QGridLayout
from PyQt5.QtGui import QFontDatabase, QIntValidator
from PyQt5.QtCore import Qt

class SettingsWindow(QWidget):
    columns = [ "Hostname", "API Key", "Tool Preheat", "Bed Preheat" ]
    presets = [ "octopi.local", "000000000_API_KEY_HERE_000000000", "0", "0" ]

    def __init__(self, parent, *args, **kwargs):
        super(SettingsWindow, self).__init__(*args, **kwargs)
        self.parent = parent

        self.setWindowTitle(parent.name + " Settings")
        self.setWindowIcon(parent.icon)

        box = QVBoxLayout()
        self.setLayout(box)

        staticSettings = QGridLayout()
        box.addLayout(staticSettings, 0)

        self.jogSpeedText = QLabel("Jog Speed")
        staticSettings.addWidget(self.jogSpeedText, 0, 0)

        self.jogSpeed = QLineEdit(str(self.parent.jogMoveSpeed))
        self.jogSpeed.setValidator(QIntValidator(1, 6000))
        staticSettings.addWidget(self.jogSpeed, 0, 1)

        self.jogSpeedUnitText = QLabel("mm/min")
        staticSettings.addWidget(self.jogSpeedUnitText, 0, 2)

        self.jogLengthText = QLabel("Jog Length")
        staticSettings.addWidget(self.jogLengthText, 1, 0)

        self.jogLength = QLineEdit(str(self.parent.jogMoveLength))
        self.jogLength.setValidator(QIntValidator(1, 100))
        staticSettings.addWidget(self.jogLength, 1, 1)

        self.jogLengthUnitText = QLabel("mm")
        staticSettings.addWidget(self.jogLengthUnitText, 1, 2)

        helpText = "Usage:\n"
        helpText += "1st Column: Printer Hostname or IP address\n"
        helpText += "2nd Column: OctoPrint API Key (32 char hexadecimal)\n"
        helpText += "3rd Column: Tool Preheat Temperature (0 to disable)\n"
        helpText += "4th Column: Bed Preheat Temperature (0 to disable)"
        self.helpText = QLabel(helpText)
        box.addWidget(self.helpText, 0)
        box.setAlignment(self.helpText, Qt.AlignHCenter)

        buttons = QHBoxLayout()
        box.addLayout(buttons, 0)

        self.add = QPushButton("&Add Printer")
        self.add.clicked.connect(self.addPrinter)
        buttons.addWidget(self.add)

        self.remove = QPushButton("&Remove Printer")
        self.remove.clicked.connect(self.removePrinter)
        buttons.addWidget(self.remove)

        printers = self.parent.readSettings()
        self.rows = len(printers)
        self.table = QTableWidget(self.rows, len(self.columns))
        box.addWidget(self.table, 1)

        for i in range(0, self.rows):
            p = printers[i]
            for j in range(0, len(self.columns)):
                text = p[j]
                if (j >= 2) and (j <= 3) and (text == None):
                    text = "0"
                item = QTableWidgetItem(text)
                self.table.setItem(i, j, item)
                if j == 1:
                    font = item.font()
                    font.setFamily(QFontDatabase.systemFont(QFontDatabase.FixedFont).family())
                    item.setFont(font)

        buttons2 = QHBoxLayout()
        box.addLayout(buttons2, 0)

        self.up = QPushButton("Move &Up")
        self.up.clicked.connect(self.moveUp)
        buttons2.addWidget(self.up)

        self.down = QPushButton("Move &Down")
        self.down.clicked.connect(self.moveDown)
        buttons2.addWidget(self.down)

        self.openWeb = QPushButton("&Open Web UI of selected")
        self.openWeb.clicked.connect(self.openWebUI)
        box.addWidget(self.openWeb, 0)

        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows);
        self.table.resizeColumnsToContents()

        if self.rows <= 0:
            self.addPrinter()

    def tableToList(self):
        printers = []
        for i in range(0, self.rows):
            p = []
            for j in range(0, len(self.columns)):
                text = self.table.item(i, j).text()
                if (j >= 2) and (j <= 3) and (text == "0"):
                    text = None
                p.append(text)
            printers.append(p)
        return printers

    def settingsValid(self, printers):
        for p in printers:
            # p[0] needs to be valid hostname or IP
            # TODO

            # p[1] needs to be valid API key (hexadecimal, 32 chars)
            if (len(p[1]) != 32) or not all(c in string.hexdigits for c in p[1]):
                return (False, "API Key not 32-digit hexadecimal")

            # p[2] and p[3] need to be integer temperatures (0...999)
            for s in [ p[2], p[3] ]:
                if s == None:
                    s = "0"
                if (len(s) < 1) or (len(s) > 3) or not all(c in string.digits for c in s):
                    return (False, "Temperature not a number from 0...999")

        js = int(self.jogSpeed.text())
        if (js < 1) or (js > 6000):
            return (False, "Jog Speed not a number from 1...6000")

        jl = int(self.jogLength.text())
        if (jl < 1) or (jl > 100):
            return (False, "Jog Length not a number from 1...100")

        return (True, "")

    def closeEvent(self, event):
        oldPrinters = [item[0:len(self.columns)] for item in self.parent.printers]
        newPrinters = self.tableToList()

        valid, errorText = self.settingsValid(newPrinters)
        if valid == False:
            r = self.parent.showDialog(self.parent.name + " Settings Invalid", errorText + "!", "Do you want to edit it again?", True, True, False)
            if r == True:
                event.ignore()
                return
            else:
                self.parent.removeSettingsWindow()
                return

        js = int(self.jogSpeed.text())
        jl = int(self.jogLength.text())

        if (oldPrinters != newPrinters) or (js != self.parent.jogMoveSpeed) or (jl != self.parent.jogMoveLength):
            r = self.parent.showDialog(self.parent.name + " Settings Changed", "Do you want to save the new configuration?", "This will restart the application!", True, False, False)
            if r == True:
                self.parent.jogMoveSpeed = js
                self.parent.jogMoveLength = jl
                self.parent.writeSettings(newPrinters)
                self.parent.restartApp()

        self.parent.removeSettingsWindow()

    def addPrinter(self):
        self.rows += 1
        self.table.setRowCount(self.rows)
        for i in range(0, len(self.columns)):
            item = QTableWidgetItem(self.presets[i])
            self.table.setItem(self.rows - 1, i, item)
            if i == 1:
                font = item.font()
                font.setFamily(QFontDatabase.systemFont(QFontDatabase.FixedFont).family())
                item.setFont(font)
        self.table.resizeColumnsToContents()
        self.table.setCurrentItem(self.table.item(self.rows - 1, 0))

    def removePrinter(self):
        r = self.table.currentRow()
        if (r >= 0) and (r < self.rows):
            self.rows -= 1
            self.table.removeRow(r)
            self.table.setCurrentItem(self.table.item(min(r, self.rows - 1), 0))

    def moveUp(self):
        i = self.table.currentRow()
        if i <= 0:
            return
        host = self.table.item(i, 0).text()
        key = self.table.item(i, 1).text()
        self.table.item(i, 0).setText(self.table.item(i - 1, 0).text())
        self.table.item(i, 1).setText(self.table.item(i - 1, 1).text())
        self.table.item(i - 1, 0).setText(host)
        self.table.item(i - 1, 1).setText(key)
        self.table.setCurrentItem(self.table.item(i - 1, 0))

    def moveDown(self):
        i = self.table.currentRow()
        if i >= (self.rows - 1):
            return
        host = self.table.item(i, 0).text()
        key = self.table.item(i, 1).text()
        self.table.item(i, 0).setText(self.table.item(i + 1, 0).text())
        self.table.item(i, 1).setText(self.table.item(i + 1, 1).text())
        self.table.item(i + 1, 0).setText(host)
        self.table.item(i + 1, 1).setText(key)
        self.table.setCurrentItem(self.table.item(i + 1, 0))

    def openWebUI(self):
        host = self.table.item(self.table.currentRow(), 0).text()
        self.parent.openBrowser(host)
