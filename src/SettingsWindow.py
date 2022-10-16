#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# SettingsWindow.py
#
# UI for changes to application configuration.

import string
import pprint
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QGridLayout, QComboBox
from PyQt5.QtGui import QFontDatabase, QIntValidator
from PyQt5.QtCore import Qt

class Printer(object):
    # field 'api' for actual I/O
    # field 'host' etc. for settings

    def __repr__(self):
        return pprint.pformat(vars(self))

class SettingsWindow(QWidget):
    genericColumns = [
        ( "Hostname", "octopi.local" ),
        ( "Interface", "OctoPrint" ),
        ( "Tool Temp", "0" ),
        ( "Bed Temp", "0" ),
        ( "Jog Speed", "600" ),
        ( "Jog Length", "10" ),
    ]

    apiColumns = [
        ( "OctoPrint", [
            ( "API Key", "000000000_API_KEY_HERE_000000000", [] )
        ]),
        ( "Moonraker", [
            ( "Webcam", "0", [] )
        ]),
    ]

    def __init__(self, parent, *args, **kwargs):
        super(SettingsWindow, self).__init__(*args, **kwargs)
        self.parent = parent

        self.setWindowTitle(parent.name + " Settings")
        self.setWindowIcon(parent.icon)

        box = QVBoxLayout()
        self.setLayout(box)

        self.openWeb = QPushButton("&Open Web UI of selected")
        self.openWeb.clicked.connect(self.openWebUI)
        box.addWidget(self.openWeb, 0)

        buttons = QHBoxLayout()
        box.addLayout(buttons, 0)

        self.add = QPushButton("&Add Printer")
        self.add.clicked.connect(self.addPrinter)
        buttons.addWidget(self.add)

        self.remove = QPushButton("&Remove Printer")
        self.remove.clicked.connect(self.removePrinter)
        buttons.addWidget(self.remove)

        buttons2 = QHBoxLayout()
        box.addLayout(buttons2, 0)

        self.up = QPushButton("Move &Up")
        self.up.clicked.connect(self.moveUp)
        buttons2.addWidget(self.up)

        self.down = QPushButton("Move &Down")
        self.down.clicked.connect(self.moveDown)
        buttons2.addWidget(self.down)

        # Printer data from OctoTray settings
        self.data = self.parent.readSettings()
        self.originalData = self.data.copy()

        # Table of printers
        self.printerCount = len(self.data)
        self.printers = QTableWidget(self.printerCount, len(self.genericColumns))
        box.addWidget(self.printers, 1)

        # Populate table of printers
        for i in range(0, self.printerCount):
            p = self.data[i]

            # hostname in first column
            item = QTableWidgetItem(p.host)
            self.printers.setItem(i, 0, item)

            font = item.font()
            font.setFamily(QFontDatabase.systemFont(QFontDatabase.FixedFont).family())
            item.setFont(font)

            # API selection in second column
            item = QComboBox()
            for api, options in self.apiColumns:
                item.addItem(api)
                if p.apiType == api:
                    item.setCurrentText(api)
            item.currentIndexChanged.connect(self.selectionChanged)
            self.printers.setCellWidget(i, 1, item)

            # Tool Temp in third column
            item = QTableWidgetItem(p.tempTool)
            self.printers.setItem(i, 2, item)

            # Bed Temp in fourth column
            item = QTableWidgetItem(p.tempBed)
            self.printers.setItem(i, 3, item)

            # Jog Speed in fifth column
            item = QTableWidgetItem(p.jogSpeed)
            self.printers.setItem(i, 4, item)

            # Jog Length in sixth column
            item = QTableWidgetItem(p.jogLength)
            self.printers.setItem(i, 5, item)

            self.apiColumns[0][1][0][2].append(p.key)
            self.apiColumns[1][1][0][2].append(p.webcam)

        # Table of settings
        self.settings = QTableWidget(1, 2)
        box.addWidget(self.settings, 1)

        # Callback to update settings when printers selection changes
        self.printers.itemSelectionChanged.connect(self.selectionChanged)
        self.settings.itemChanged.connect(self.settingsChanged)

        # Put usage hint in settings table
        self.populateDefaultSettings()

        # Setup tables
        self.setupTableHeaders()

        # Initialize empty entry when none are available
        if len(self.data) <= 0:
            self.addPrinter()

    def setupTableHeaders(self):
        for t, tc in [
            ( self.printers, [ i[0] for i in self.genericColumns ] ),
            ( self.settings, [ "Option", "Value" ] )
        ]:
            t.setHorizontalHeaderLabels(tc)
            t.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
            t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows);
            t.resizeColumnsToContents()

    def settingsChanged(self, item):
        printer = self.printers.currentRow()
        if (printer < 0) or (item.column() < 1):
            return

        apiType = self.printers.cellWidget(printer, 1).currentText()
        if apiType == self.apiColumns[0][0]:
            self.apiColumns[0][1][item.row()][2][printer] = item.text()
        elif apiType == self.apiColumns[1][0]:
            self.apiColumns[1][1][item.row()][2][printer] = item.text()

    def populateDefaultSettings(self):
        self.settings.clear()
        self.settings.setRowCount(1)
        self.settings.setColumnCount(2)

        item = QTableWidgetItem("Select printer for")
        self.settings.setItem(0, 0, item)
        item = QTableWidgetItem("detailed settings")
        self.settings.setItem(0, 1, item)

        self.setupTableHeaders()
        self.settings.resizeColumnsToContents()

    def selectionChanged(self):
        i = self.printers.currentRow()
        apiType = self.printers.cellWidget(i, 1).currentText()
        for api, nv in self.apiColumns:
            if api == apiType:
                self.settings.clear()
                self.settings.setRowCount(len(nv))
                self.settings.setColumnCount(2)

                n = 0
                for name, value, data in nv:
                    item = QTableWidgetItem(name)
                    self.settings.setItem(n, 0, item)
                    item = QTableWidgetItem(data[i])
                    self.settings.setItem(n, 1, item)
                    n += 1

                self.setupTableHeaders()
                self.settings.resizeColumnsToContents()
                return

        self.populateDefaultSettings()

    def printersToList(self):
        printers = []
        for i in range(0, self.printerCount):
            p = Printer()

            p.host = self.printers.item(i, 0).text()
            p.apiType = self.printers.cellWidget(i, 1).currentText()
            p.tempTool = self.printers.item(i, 2).text()
            p.tempBed = self.printers.item(i, 3).text()
            p.jogSpeed = self.printers.item(i, 4).text()
            p.jogLength = self.printers.item(i, 5).text()
            p.key = self.apiColumns[0][1][0][2][i]
            p.webcam = self.apiColumns[1][1][0][2][i]

            printers.append(p)
        return printers

    def settingsValid(self, printers):
        for p in printers:
            # p.host needs to be valid hostname or IP
            # TODO

            # p.apiType
            # TODO

            if p.apiType == self.apiColumns[0][0]:
                # p.key only for octoprint
                # p.key needs to be valid API key (hexadecimal, 32 chars)
                if (len(p.key) != 32) or not all(c in string.hexdigits for c in p.key):
                    return (False, "API Key not 32-digit hexadecimal")
            elif p.apiType == self.apiColumns[1][0]:
                # p.webcam only for moonraker
                if (len(p.webcam) < 1) or (len(p.webcam) > 1) or not all(c in string.digits for c in p.webcam):
                    return (False, "Webcam ID not a number from 0...9")

            # p.tempTool and p.tempBed need to be integer temperatures (0...999)
            for s in [ p.tempTool, p.tempBed ]:
                if s == None:
                    s = "0"
                if (len(s) < 1) or (len(s) > 3) or not all(c in string.digits for c in s):
                    return (False, "Temperature not a number from 0...999")

                js = p.jogSpeed
                if js == None:
                    js = "0"
                if (len(js) < 1) or (len(js) > 3) or not all(c in string.digits for c in js) or (int(js) < 0) or (int(js) > 6000):
                    return (False, "Jog Speed not a number from 0...6000")

                jl = p.jogLength
                if jl == None:
                    jl = "0"
                if (len(jl) < 1) or (len(jl) > 3) or not all(c in string.digits for c in jl) or (int(jl) < 0) or (int(jl) > 100):
                    return (False, "Jog Length not a number from 0...100")

        return (True, "")

    def printerDiffers(self, a, b):
        if (a.host != b.host) or (a.key != b.key) or (a.tempTool != b.tempTool) or (a.tempBed != b.tempBed) or (a.jogSpeed != b.jogSpeed) or (a.jogLength != b.jogLength) or (a.webcam != b.webcam):
            return True
        return False

    def printersDiffer(self, a, b):
        if (len(a) != len(b)):
            return True

        for i in range(0, len(a)):
            if self.printerDiffers(a[i], b[i]):
                return True

        return False

    def closeEvent(self, event):
        oldPrinters = self.parent.printers
        newPrinters = self.printersToList()

        valid, errorText = self.settingsValid(newPrinters)
        if valid == False:
            r = self.parent.showDialog(self.parent.name + " Settings Invalid", errorText + "!", "Do you want to edit it again?", True, True, False)
            if r == True:
                event.ignore()
                return
            else:
                self.parent.removeSettingsWindow()
                return

        if self.printersDiffer(oldPrinters, newPrinters):
            r = self.parent.showDialog(self.parent.name + " Settings Changed", "Do you want to save the new configuration?", "This will restart the application!", True, False, False)
            if r == True:
                self.parent.writeSettings(newPrinters)
                self.parent.removeSettingsWindow()
                self.parent.restartApp()

        self.parent.removeSettingsWindow()

    def addPrinter(self):
        self.printerCount += 1
        self.printers.setRowCount(self.printerCount)
        for i in range(0, len(self.genericColumns)):
            if i != 1:
                item = QTableWidgetItem(self.genericColumns[i][1])
                self.printers.setItem(self.printerCount - 1, i, item)
                if i == 0:
                    font = item.font()
                    font.setFamily(QFontDatabase.systemFont(QFontDatabase.FixedFont).family())
                    item.setFont(font)
            else:
                item = QComboBox()
                for api, options in self.apiColumns:
                    item.addItem(api)
                    if self.genericColumns[i][1] == api:
                        item.setCurrentText(api)
                item.currentIndexChanged.connect(self.selectionChanged)
                self.printers.setCellWidget(self.printerCount - 1, i, item)

        # add default values for api specific settings
        self.apiColumns[0][1][0][2].append(self.apiColumns[0][1][0][1])
        self.apiColumns[1][1][0][2].append(self.apiColumns[1][1][0][1])

        self.printers.resizeColumnsToContents()
        self.printers.setCurrentItem(self.printers.item(self.printerCount - 1, 0))

    def removePrinter(self):
        r = self.printers.currentRow()
        if (r >= 0) and (r < self.printerCount):
            self.printerCount -= 1
            self.printers.removeRow(r)
            self.printers.setCurrentItem(self.printers.item(min(r, self.printerCount - 1), 0))

            # also remove values for api specific settings
            del self.apiColumns[0][1][0][2][r]
            del self.apiColumns[1][1][0][2][r]

    def moveUp(self):
        i = self.printers.currentRow()
        if i <= 0:
            return

        for c in range(0, self.printers.columnCount()):
            if c != 1:
                a = self.printers.takeItem(i, c)
                b = self.printers.takeItem(i - 1, c)
                self.printers.setItem(i, c, b)
                self.printers.setItem(i - 1, c, a)
            else:
                a = self.printers.cellWidget(i, c).currentText()
                b = self.printers.cellWidget(i - 1, c).currentText()
                self.printers.cellWidget(i, c).setCurrentText(b)
                self.printers.cellWidget(i - 1, c).setCurrentText(a)

        # also move values for api specific settings
        for v in [ self.apiColumns[0][1][0][2], self.apiColumns[1][1][0][2] ]:
            a = v[i]
            b = v[i - 1]
            v[i] = b
            v[i - 1] = a

        self.printers.setCurrentItem(self.printers.item(i - 1, 0))

    def moveDown(self):
        i = self.printers.currentRow()
        if i >= (self.printerCount - 1):
            return

        for c in range(0, self.printers.columnCount()):
            if c != 1:
                a = self.printers.takeItem(i, c)
                b = self.printers.takeItem(i + 1, c)
                self.printers.setItem(i, c, b)
                self.printers.setItem(i + 1, c, a)
            else:
                a = self.printers.cellWidget(i, c).currentText()
                b = self.printers.cellWidget(i + 1, c).currentText()
                self.printers.cellWidget(i, c).setCurrentText(b)
                self.printers.cellWidget(i + 1, c).setCurrentText(a)

        # also move values for api specific settings
        for v in [ self.apiColumns[0][1][0][2], self.apiColumns[1][1][0][2] ]:
            a = v[i]
            b = v[i + 1]
            v[i] = b
            v[i + 1] = a

        self.printers.setCurrentItem(self.printers.item(i + 1, 0))

    def openWebUI(self):
        host = self.printers.item(self.printers.currentRow(), 0).text()
        self.parent.openBrowser(host)
