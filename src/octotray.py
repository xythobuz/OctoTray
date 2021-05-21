#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# depends on:
# - python-pyqt5
#
# see also:
# https://doc.qt.io/qt-5/qtwidgets-widgets-imageviewer-example.html
# https://stackoverflow.com/a/22618496

import json
import sys
import os
import time
import urllib.parse
import urllib.request
from os import path
from PyQt5 import QtWidgets, QtGui, QtCore, QtNetwork
from PyQt5.QtWidgets import QSystemTrayIcon, QAction, QMenu, QMessageBox, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QDesktopWidget, QSizePolicy, QSlider, QLayout, QTableWidget, QTableWidgetItem, QPushButton
from PyQt5.QtGui import QIcon, QPixmap, QImageReader, QDesktopServices
from PyQt5.QtCore import QCoreApplication, QSettings, QUrl, QTimer, QSize, Qt, QSettings

class SettingsWindow(QWidget):
    def __init__(self, parent, *args, **kwargs):
        super(SettingsWindow, self).__init__(*args, **kwargs)
        self.parent = parent

        self.setWindowTitle(parent.name + " Settings")
        self.setWindowIcon(parent.icon)

        box = QVBoxLayout()
        self.setLayout(box)

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
        self.table = QTableWidget(self.rows, 2)
        box.addWidget(self.table, 1)

        for i in range(0, self.rows):
            p = printers[i]
            for j in range(0, 2):
                item = QTableWidgetItem(p[j])
                self.table.setItem(i, j, item)

        buttons2 = QHBoxLayout()
        box.addLayout(buttons2, 0)

        self.up = QPushButton("Move &Up")
        self.up.clicked.connect(self.moveUp)
        buttons2.addWidget(self.up)

        self.down = QPushButton("Move &Down")
        self.down.clicked.connect(self.moveDown)
        buttons2.addWidget(self.down)

        self.table.setHorizontalHeaderLabels(["Hostname", "API Key"])
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.table.resizeColumnsToContents()

        if self.rows <= 0:
            self.addPrinter()

    def tableToList(self):
        printers = []
        for i in range(0, self.rows):
            p = [self.table.item(i, 0).text(), self.table.item(i, 1).text()]
            printers.append(p)
        return printers

    def closeEvent(self, event):
        oldPrinters = [item[0:2] for item in self.parent.printers]
        newPrinters = self.tableToList()
        if oldPrinters != newPrinters:
            r = self.parent.showDialog(self.parent.name + " Settings Changed", "Do you want to save the new list of printers?", "This will restart the application!", True, False, False)
            if r == True:
                self.parent.writeSettings(newPrinters)
                self.parent.restartApp()
        self.parent.removeSettingsWindow()

    def addPrinter(self):
        self.rows += 1
        self.table.setRowCount(self.rows)
        self.table.setItem(self.rows - 1, 0, QTableWidgetItem("HOSTNAME"))
        self.table.setItem(self.rows - 1, 1, QTableWidgetItem("API_KEY"))
        self.table.resizeColumnsToContents()

    def removePrinter(self):
        r = self.table.currentRow()
        if (r >= 0) and (r < self.rows):
            self.rows -= 1
            self.table.removeRow(r)

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

class AspectRatioPixmapLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super(AspectRatioPixmapLabel, self).__init__(*args, **kwargs)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self.pix = QPixmap(0, 0)

    def setPixmap(self, p):
        self.pix = p
        super(AspectRatioPixmapLabel, self).setPixmap(self.scaledPixmap())

    def heightForWidth(self, width):
        if self.pix.isNull():
            return self.height()
        else:
            return (self.pix.height() * width) / self.pix.width()

    def sizeHint(self):
        w = self.width()
        return QSize(int(w), int(self.heightForWidth(w)))

    def scaledPixmap(self):
        return self.pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def resizeEvent(self, e):
        if not self.pix.isNull():
            super(AspectRatioPixmapLabel, self).setPixmap(self.scaledPixmap())

class CamWindow(QWidget):
    reloadDelayDefault = 1000 # in ms
    statusDelay = 10 * 1000 # in ms
    addSize = 100
    reloadOn = True

    def __init__(self, parent, printer, *args, **kwargs):
        super(CamWindow, self).__init__(*args, **kwargs)
        self.app = parent.app
        self.manager = parent.manager
        self.manager.finished.connect(self.handleResponse)
        self.parent = parent
        self.printer = printer
        self.host = self.printer[0]
        self.url = "http://" + self.host + ":8080/?action=snapshot"

        self.setWindowTitle(parent.name + " Webcam Stream")
        self.setWindowIcon(parent.icon)

        box = QVBoxLayout()
        self.setLayout(box)

        label = QLabel(self.url)
        box.addWidget(label, 0)
        box.setAlignment(label, Qt.AlignHCenter)

        self.img = AspectRatioPixmapLabel()
        self.img.setPixmap(QPixmap(640, 480))
        box.addWidget(self.img, 1)

        slide = QHBoxLayout()
        box.addLayout(slide, 0)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(2000)
        self.slider.setTickInterval(100)
        self.slider.setPageStep(100)
        self.slider.setSingleStep(100)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setValue(self.reloadDelayDefault)
        self.slider.valueChanged.connect(self.sliderChanged)
        slide.addWidget(self.slider, 1)

        self.slideLabel = QLabel(str(self.reloadDelayDefault) + "ms")
        slide.addWidget(self.slideLabel, 0)

        self.statusLabel = QLabel("Status: unavailable")
        box.addWidget(self.statusLabel, 0)
        box.setAlignment(label, Qt.AlignHCenter)

        size = self.size()
        size.setHeight(size.height() + self.addSize)
        self.resize(size)

        self.loadImage()
        self.loadStatus()

    def getHost(self):
        return self.host

    def sliderChanged(self):
        self.slideLabel.setText(str(self.slider.value()) + "ms")

    def closeEvent(self, event):
        self.reloadOn = False
        self.url = ""
        self.parent.removeWebcamWindow(self)

    def scheduleLoadImage(self):
        if self.reloadOn:
            QTimer.singleShot(self.slider.value(), self.loadImage)

    def scheduleLoadStatus(self):
        if self.reloadOn:
            QTimer.singleShot(self.statusDelay, self.loadStatus)

    def loadImage(self):
        url = QUrl(self.url)
        request = QtNetwork.QNetworkRequest(url)
        self.manager.get(request)

    def loadStatus(self):
        s = "Status: "
        t = self.parent.getTemperatureString(self.host, self.printer[1])
        if len(t) > 0:
            s += t
        else:
            s += "Unknown"

        progress = self.parent.getProgress(self.host, self.printer[1])
        if ("completion" in progress) and ("printTime" in progress) and ("printTimeLeft" in progress) and (progress["completion"] != None) and (progress["printTime"] != None) and (progress["printTimeLeft"] != None):
            s += " - %.1f%%" % progress["completion"]
            s += " - runtime "
            s += time.strftime("%H:%M:%S", time.gmtime(progress["printTime"]))
            s += " - "
            s += time.strftime("%H:%M:%S", time.gmtime(progress["printTimeLeft"])) + " left"

        self.statusLabel.setText(s)
        self.scheduleLoadStatus()

    def handleResponse(self, reply):
        if reply.url().url() == self.url:
            if reply.error() == QtNetwork.QNetworkReply.NoError:
                reader = QImageReader(reply)
                reader.setAutoTransform(True)
                image = reader.read()
                if image != None:
                    if image.colorSpace().isValid():
                        image.convertToColorSpace(QColorSpace.SRgb)
                    self.img.setPixmap(QPixmap.fromImage(image))
                    self.scheduleLoadImage()
                else:
                    print("Error decoding image: " + reader.errorString())
            else:
                print("Error loading image: " + reply.errorString())

class OctoTray():
    name = "OctoTray"
    vendor = "xythobuz"
    version = "0.3"

    iconName = "octotray_icon.png"
    iconPaths = [
        path.abspath(path.dirname(__file__)),
        "data",
        "/usr/share/pixmaps",
        ".",
        "..",
        "../data"
    ]

    networkTimeout = 2.0 # in s

    # list of lists, inner lists contain printer data:
    # 0=host 1=key (2=system-commands 3=menu 4+=actions)
    printers = []
    
    statesWithWarning = [
        "Printing", "Pausing", "Paused"
    ]

    camWindows = []
    settingsWindow = None

    def __init__(self, app):
        QCoreApplication.setApplicationName(self.name)
        self.app = app

        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.showDialog("OctoTray Error", "System Tray is not available on this platform!", "", False, False, True)
            sys.exit(0)

        self.manager = QtNetwork.QNetworkAccessManager()
        self.menu = QMenu()
        self.printers = self.readSettings()

        unknownCount = 0
        for p in self.printers:
            method = self.getMethod(p[0], p[1])
            print("Printer " + p[0] + " has method " + method)
            if method == "unknown":
                unknownCount += 1

                action = QAction(p[0])
                action.setEnabled(False)
                p.append(action)
                self.menu.addAction(action)

                continue

            commands = self.getSystemCommands(p[0], p[1])
            p.append(commands)

            menu = QMenu(self.getName(p[0], p[1]))
            p.append(menu)
            self.menu.addMenu(menu)

            if method == "psucontrol":
                action = QAction("Turn On PSU")
                action.triggered.connect(lambda chk, x=p: self.printerOnAction(x))
                p.append(action)
                menu.addAction(action)

                action = QAction("Turn Off PSU")
                action.triggered.connect(lambda chk, x=p: self.printerOffAction(x))
                p.append(action)
                menu.addAction(action)

            for i in range(0, len(commands)):
                action = QAction(commands[i].title())
                action.triggered.connect(lambda chk, x=p, y=i: self.printerSystemCommandAction(x, y))
                p.append(action)
                menu.addAction(action)

            menu.addSeparator()

            action = QAction("Get Status")
            action.triggered.connect(lambda chk, x=p: self.printerStatusAction(x))
            p.append(action)
            menu.addAction(action)

            action = QAction("Show Webcam")
            action.triggered.connect(lambda chk, x=p: self.printerWebcamAction(x))
            p.append(action)
            menu.addAction(action)

            action = QAction("Open Web UI")
            action.triggered.connect(lambda chk, x=p: self.printerWebAction(x))
            p.append(action)
            menu.addAction(action)

        self.menu.addSeparator()

        self.settingsAction = QAction("&Settings")
        self.settingsAction.triggered.connect(self.showSettingsAction)
        self.menu.addAction(self.settingsAction)

        self.refreshAction = QAction("&Refresh")
        self.refreshAction.triggered.connect(self.restartApp)
        self.menu.addAction(self.refreshAction)

        self.quitAction = QAction("&Quit")
        self.quitAction.triggered.connect(self.exit)
        self.menu.addAction(self.quitAction)

        self.iconPathName = None
        for p in self.iconPaths:
            if os.path.isfile(path.join(p, self.iconName)):
                self.iconPathName = path.join(p, self.iconName)
                break
        if self.iconPathName == None:
            self.showDialog("OctoTray Error", "Icon file has not been found!", "", False, False, True)
            sys.exit(0)

        self.icon = QIcon()
        self.pic = QPixmap(32, 32)
        self.pic.load(self.iconPathName)
        self.icon = QIcon(self.pic)

        self.trayIcon = QSystemTrayIcon(self.icon)
        self.trayIcon.setToolTip(self.name + " " + self.version)
        self.trayIcon.setContextMenu(self.menu)
        self.trayIcon.setVisible(True)

    def readSettings(self):
        settings = QSettings(self.vendor, self.name)
        printers = []
        l = settings.beginReadArray("printers")
        for i in range(0, l):
            settings.setArrayIndex(i)
            p = []
            p.append(settings.value("host"))
            p.append(settings.value("key"))
            printers.append(p)
        settings.endArray()
        return printers

    def writeSettings(self, printers):
        settings = QSettings(self.vendor, self.name)
        settings.remove("printers")
        settings.beginWriteArray("printers")
        for i in range(0, len(printers)):
            p = printers[i]
            settings.setArrayIndex(i)
            settings.setValue("host", p[0])
            settings.setValue("key", p[1])
        settings.endArray()
        del settings

    def openBrowser(self, url):
        QDesktopServices.openUrl(QUrl("http://" + url))

    def showDialog(self, title, text1, text2 = "", question = False, warning = False, error = False):
        msg = QMessageBox()

        if error:
            msg.setIcon(QMessageBox.Critical)
        elif warning:
            msg.setIcon(QMessageBox.Warning)
        elif question:
            msg.setIcon(QMessageBox.Question)
        else:
            msg.setIcon(QMessageBox.Information)

        msg.setWindowTitle(title)
        msg.setText(text1)

        if text2 is not None:
            msg.setInformativeText(text2)

        if question:
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        else:
            msg.setStandardButtons(QMessageBox.Ok)

        retval = msg.exec_()
        if retval == QMessageBox.Yes:
            return True
        else:
            return False

    def sendRequest(self, host, headers, path, content = None):
        url = "http://" + host + "/api/" + path
        if content == None:
            request = urllib.request.Request(url, None, headers)
        else:
            data = content.encode('ascii')
            request = urllib.request.Request(url, data, headers)

        try:
            with urllib.request.urlopen(request, None, self.networkTimeout) as response:
                text = response.read()
                return text
        except (urllib.error.URLError, urllib.error.HTTPError) as error:
            print("Error requesting URL \"" + url + "\": \"" + str(error) + "\"")
            return "error"
        except socket.timeout:
            print("Timeout waiting for response to \"" + url + "\"")
            return "timeout"

    def sendPostRequest(self, host, key, path, content):
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": key
        }
        return self.sendRequest(host, headers, path, content)

    def sendGetRequest(self, host, key, path):
        headers = {
            "X-Api-Key": key
        }
        return self.sendRequest(host, headers, path)

    def getTemperatureString(self, host, key):
        r = self.sendGetRequest(host, key, "printer")
        s = ""
        try:
            rd = json.loads(r)

            if ("state" in rd) and ("text" in rd["state"]):
                s += rd["state"]["text"]
                if "temperature" in rd:
                    s += " - "

            if "temperature" in rd:
                if "bed" in rd["temperature"]:
                    if "actual" in rd["temperature"]["bed"]:
                        s += "B"
                        s += "%.1f" % rd["temperature"]["bed"]["actual"]
                        if "target" in rd["temperature"]["bed"]:
                            s += "/"
                            s += "%.1f" % rd["temperature"]["bed"]["target"]
                        s += " "

                if "tool0" in rd["temperature"]:
                    if "actual" in rd["temperature"]["tool0"]:
                        s += "T"
                        s += "%.1f" % rd["temperature"]["tool0"]["actual"]
                        if "target" in rd["temperature"]["tool0"]:
                            s += "/"
                            s += "%.1f" % rd["temperature"]["tool0"]["target"]
                        s += " "

                if "tool1" in rd["temperature"]:
                    if "actual" in rd["temperature"]["tool1"]:
                        s += "T"
                        s += "%.1f" % rd["temperature"]["tool1"]["actual"]
                        if "target" in rd["temperature"]["tool1"]:
                            s += "/"
                            s += "%.1f" % rd["temperature"]["tool1"]["target"]
                        s += " "
        except json.JSONDecodeError:
            pass
        return s.strip()

    def getState(self, host, key):
        r = self.sendGetRequest(host, key, "job")
        try:
            rd = json.loads(r)
            if "state" in rd:
                return rd["state"]
        except json.JSONDecodeError:
            pass
        return "Unknown"

    def getProgress(self, host, key):
        r = self.sendGetRequest(host, key, "job")
        try:
            rd = json.loads(r)
            if "progress" in rd:
                return rd["progress"]
        except json.JSONDecodeError:
            pass
        return "Unknown"

    def getName(self, host, key):
        r = self.sendGetRequest(host, key, "printerprofiles")
        try:
            rd = json.loads(r)
            if "profiles" in rd:
                p = next(iter(rd["profiles"]))
                if "name" in rd["profiles"][p]:
                    return rd["profiles"][p]["name"]
        except json.JSONDecodeError:
            pass
        return host

    def getMethod(self, host, key):
        r = self.sendGetRequest(host, key, "plugin/psucontrol")
        if r == "timeout":
            return "unknown"

        try:
            rd = json.loads(r)
            if "isPSUOn" in rd:
                return "psucontrol"
        except json.JSONDecodeError:
            pass

        r = self.sendGetRequest(host, key, "system/commands/custom")
        if r == "timeout":
            return "unknown"

        try:
            rd = json.loads(r)
            for c in rd:
                if "action" in c:
                    # we have some custom commands and no psucontrol
                    # so lets try to use that instead of skipping
                    # the printer completely with 'unknown'
                    return "system"
        except json.JSONDecodeError:
            pass

        return "unknown"

    def getSystemCommands(self, host, key):
        l = []
        r = self.sendGetRequest(host, key, "system/commands/custom")
        try:
            rd = json.loads(r)

            if len(rd) > 0:
                print("system commands available for " + host + ":")

            for c in rd:
                if "action" in c:
                    print("  - " + c["action"])
                    l.append(c["action"])
        except json.JSONDecodeError:
            pass
        return l

    def setPSUControl(self, host, key, state):
        cmd = "turnPSUOff"
        if state:
            cmd = "turnPSUOn"
        return self.sendPostRequest(host, key, "plugin/psucontrol", '{ "command":"' + cmd + '" }')

    def setSystemCommand(self, host, key, cmd):
        cmd = urllib.parse.quote(cmd)
        return self.sendPostRequest(host, key, "system/commands/custom/" + cmd, '')

    def exit(self):
        QCoreApplication.quit()

    def printerSystemCommandAction(self, item, index):
        if "off" in item[2][index].lower():
            state = self.getState(item[0], item[1])
            if state in self.statesWithWarning:
                if self.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to run '" + item[2][index] + "'?", True, True) == True:
                    self.setSystemCommand(item[0], item[1], item[2][index])
                else:
                    return
        self.setSystemCommand(item[0], item[1], item[2][index])

    def printerOnAction(self, item):
        self.setPSUControl(item[0], item[1], True)

    def printerOffAction(self, item):
        state = self.getState(item[0], item[1])
        if state in self.statesWithWarning:
            if self.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to turn it off?", True, True) == True:
                self.setPSUControl(item[0], item[1], False)
        else:
            self.setPSUControl(item[0], item[1], False)

    def printerWebAction(self, item):
        self.openBrowser(item[0])

    def printerStatusAction(self, item):
        progress = self.getProgress(item[0], item[1])
        s = item[0] + "\n"
        warning = False
        if ("completion" in progress) and ("printTime" in progress) and ("printTimeLeft" in progress) and (progress["completion"] != None) and (progress["printTime"] != None) and (progress["printTimeLeft"] != None):
            s += "%.1f%% Completion\n" % progress["completion"]
            s += "Printing since " + time.strftime("%H:%M:%S", time.gmtime(progress["printTime"])) + "\n"
            s += time.strftime("%H:%M:%S", time.gmtime(progress["printTimeLeft"])) + " left"
        elif ("completion" in progress) and ("printTime" in progress) and ("printTimeLeft" in progress):
            s += "No job is currently running"
        else:
            s += "Could not read printer status!"
            warning = True
        t = self.getTemperatureString(item[0], item[1])
        if len(t) > 0:
            s += "\n" + t
        self.showDialog("OctoTray Status", s, None, False, warning)

    def printerWebcamAction(self, item):
        for cw in self.camWindows:
            if cw.getHost() == item[0]:
                cw.show()
                cw.activateWindow()
                return

        window = CamWindow(self, item)
        self.camWindows.append(window)

        window.show()
        window.activateWindow()

        screenGeometry = QDesktopWidget().screenGeometry()
        x = (screenGeometry.width() - window.width()) / 2
        y = (screenGeometry.height() - window.height()) / 2
        x += screenGeometry.x()
        y += screenGeometry.y()
        window.setGeometry(int(x), int(y), int(window.width()), int(window.height()))

    def removeWebcamWindow(self, window):
        self.camWindows.remove(window)

    def showSettingsAction(self):
        if self.settingsWindow != None:
            self.settingsWindow.show()
            self.settingsWindow.activateWindow()
            return

        self.settingsWindow = SettingsWindow(self)
        self.settingsWindow.show()
        self.settingsWindow.activateWindow()

        screenGeometry = QDesktopWidget().screenGeometry()
        x = (screenGeometry.width() - self.settingsWindow.width()) / 2
        y = (screenGeometry.height() - self.settingsWindow.height()) / 2
        x += screenGeometry.x()
        y += screenGeometry.y()
        self.settingsWindow.setGeometry(int(x), int(y), int(self.settingsWindow.width()), int(self.settingsWindow.height()))

    def removeSettingsWindow(self):
        self.settingsWindow = None

    def restartApp(self):
        QCoreApplication.exit(42)

    def closeAll(self):
        for cw in self.camWindows:
            cw.close()

        if self.settingsWindow != None:
            self.settingsWindow.close()

        self.trayIcon.setVisible(False)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    tray = OctoTray(app)
    rc = app.exec_()

    while rc == 42:
        tray.closeAll()
        tray = OctoTray(app)
        rc = app.exec_()

    sys.exit(rc)
