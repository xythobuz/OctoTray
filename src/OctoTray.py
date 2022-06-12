#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# OctoTray.py
#
# Main application logic.

import json
import sys
import time
import urllib.parse
import urllib.request
import operator
import socket
from os import path
from PyQt5 import QtNetwork
from PyQt5.QtWidgets import QSystemTrayIcon, QAction, QMenu, QMessageBox, QDesktopWidget
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices, QCursor
from PyQt5.QtCore import QCoreApplication, QSettings, QUrl
from CamWindow import CamWindow
from SettingsWindow import SettingsWindow
from MainWindow import MainWindow

class OctoTray():
    name = "OctoTray"
    vendor = "xythobuz"
    version = "0.4"

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
    # first elements as in SettingsWindow.columns
    # 0=host 1=key 2=tool-preheat 3=bed-preheat
    # rest used for system-commands, menu, actions
    printers = []

    statesWithWarning = [
        "Printing", "Pausing", "Paused"
    ]

    camWindows = []
    settingsWindow = None

    # default, can be overridden in config
    jogMoveSpeed = 10 * 60 # in mm/min
    jogMoveLength = 10 # in mm

    def __init__(self, app, inSysTray):
        QCoreApplication.setApplicationName(self.name)
        self.app = app
        self.inSysTray = inSysTray

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

            if (p[2] != None) or (p[3] != None):
                menu.addSeparator()

            if p[2] != None:
                action = QAction("Preheat Tool")
                action.triggered.connect(lambda chk, x=p: self.printerHeatTool(x))
                p.append(action)
                menu.addAction(action)

            if p[3] != None:
                action = QAction("Preheat Bed")
                action.triggered.connect(lambda chk, x=p: self.printerHeatBed(x))
                p.append(action)
                menu.addAction(action)

            if (p[2] != None) or (p[3] != None):
                action = QAction("Cooldown")
                action.triggered.connect(lambda chk, x=p: self.printerCooldown(x))
                p.append(action)
                menu.addAction(action)

            menu.addSeparator()

            fileMenu = QMenu("Recent Files")
            p.append(fileMenu)
            menu.addMenu(fileMenu)

            files = self.getRecentFiles(p[0], p[1], 10)
            for f in files:
                fileName, filePath = f
                action = QAction(fileName)
                action.triggered.connect(lambda chk, x=p, y=filePath: self.printerFilePrint(x, y))
                p.append(action)
                fileMenu.addAction(action)

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
            if path.isfile(path.join(p, self.iconName)):
                self.iconPathName = path.join(p, self.iconName)
                break
        if self.iconPathName == None:
            self.showDialog("OctoTray Error", "Icon file has not been found!", "", False, False, True)
            sys.exit(0)

        self.icon = QIcon()
        self.pic = QPixmap(32, 32)
        self.pic.load(self.iconPathName)
        self.icon = QIcon(self.pic)

        if self.inSysTray:
            self.trayIcon = QSystemTrayIcon(self.icon)
            self.trayIcon.setToolTip(self.name + " " + self.version)
            self.trayIcon.setContextMenu(self.menu)
            self.trayIcon.activated.connect(self.showHide)
            self.trayIcon.setVisible(True)
        else:
            self.mainWindow = MainWindow(self)
            self.mainWindow.show()
            self.mainWindow.activateWindow()
            screenGeometry = QDesktopWidget().screenGeometry()
            x = (screenGeometry.width() - self.mainWindow.width()) / 2
            y = (screenGeometry.height() - self.mainWindow.height()) / 2
            x += screenGeometry.x()
            y += screenGeometry.y()
            self.mainWindow.setGeometry(int(x), int(y), int(self.mainWindow.width()), int(self.mainWindow.height()))

    def showHide(self, activationReason):
        if activationReason == QSystemTrayIcon.Trigger:
            self.menu.popup(QCursor.pos())
        elif activationReason == QSystemTrayIcon.MiddleClick:
            if len(self.printers) > 0:
                self.printerWebcamAction(self.printers[0])

    def readSettings(self):
        settings = QSettings(self.vendor, self.name)

        js = settings.value("jog_speed")
        if js != None:
            self.jogMoveSpeed = int(js)

        jl = settings.value("jog_length")
        if jl != None:
            self.jogMoveLength = int(jl)

        printers = []
        l = settings.beginReadArray("printers")
        for i in range(0, l):
            settings.setArrayIndex(i)
            p = []
            p.append(settings.value("host"))
            p.append(settings.value("key"))
            p.append(settings.value("tool_preheat"))
            p.append(settings.value("bed_preheat"))
            printers.append(p)
        settings.endArray()
        return printers

    def writeSettings(self, printers):
        settings = QSettings(self.vendor, self.name)

        settings.setValue("jog_speed", self.jogMoveSpeed)
        settings.setValue("jog_length", self.jogMoveLength)

        settings.remove("printers")
        settings.beginWriteArray("printers")
        for i in range(0, len(printers)):
            p = printers[i]
            settings.setArrayIndex(i)
            settings.setValue("host", p[0])
            settings.setValue("key", p[1])
            settings.setValue("tool_preheat", p[2])
            settings.setValue("bed_preheat", p[3])
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

    def getTemperatureIsSafe(self, host, key):
        r = self.sendGetRequest(host, key, "printer")
        try:
            rd = json.loads(r)

            if "temperature" in rd:
                if ("tool0" in rd["temperature"]) and ("actual" in rd["temperature"]["tool0"]):
                    if rd["temperature"]["tool0"]["actual"] > 50.0:
                        return False

                if ("tool1" in rd["temperature"]) and ("actual" in rd["temperature"]["tool1"]):
                    if rd["temperature"]["tool1"]["actual"] > 50.0:
                        return False
        except json.JSONDecodeError:
            pass
        return True

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

    def getRecentFiles(self, host, key, count):
        r = self.sendGetRequest(host, key, "files?recursive=true")
        files = []
        try:
            rd = json.loads(r)
            if "files" in rd:
                t = [f for f in rd["files"] if "date" in f]
                fs = sorted(t, key=operator.itemgetter("date"), reverse=True)
                for f in fs[:count]:
                    files.append((f["name"], f["origin"] + "/" + f["path"]))
        except json.JSONDecodeError:
            pass
        return files

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
                if self.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to run '" + item[2][index] + "'?", True, True) == False:
                    return

            safe = self.getTemperatureIsSafe(item[0], item[1])
            if safe == False:
                if self.showDialog("OctoTray Warning", "The printer seems to still be hot!", "Do you really want to turn it off?", True, True) == False:
                    return

        self.setSystemCommand(item[0], item[1], item[2][index])

    def printerOnAction(self, item):
        self.setPSUControl(item[0], item[1], True)

    def printerOffAction(self, item):
        state = self.getState(item[0], item[1])
        if state in self.statesWithWarning:
            if self.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to turn it off?", True, True) == False:
                return

        safe = self.getTemperatureIsSafe(item[0], item[1])
        if safe == False:
            if self.showDialog("OctoTray Warning", "The printer seems to still be hot!", "Do you really want to turn it off?", True, True) == False:
                return

        self.setPSUControl(item[0], item[1], False)

    def printerHomingAction(self, item, axes = "xyz"):
        state = self.getState(item[0], item[1])
        if state in self.statesWithWarning:
            if self.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to home it?", True, True) == False:
                return

        axes_string = ''
        for i in range(0, len(axes)):
            axes_string += '"' + str(axes[i]) + '"'
            if i < (len(axes) - 1):
                axes_string += ', '

        self.sendPostRequest(item[0], item[1], "printer/printhead", '{ "command": "home", "axes": [' + axes_string + '] }')

    def printerMoveAction(self, printer, axis, dist, relative = True):
        state = self.getState(printer[0], printer[1])
        if state in self.statesWithWarning:
            if self.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to move it?", True, True) == False:
                return

        absolute = ''
        if relative == False:
            absolute = ', "absolute": true'

        self.sendPostRequest(printer[0], printer[1], "printer/printhead", '{ "command": "jog", "' + str(axis) + '": ' + str(dist) + ', "speed": ' + str(self.jogMoveSpeed) + absolute + ' }')

    def printerPauseResume(self, printer):
        state = self.getState(printer[0], printer[1])
        if state in self.statesWithWarning:
            if self.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to pause/resume?", True, True) == False:
                return
        self.sendPostRequest(printer[0], printer[1], "job", '{ "command": "pause", "action": "toggle" }')

    def printerJobCancel(self, printer):
        state = self.getState(printer[0], printer[1])
        if state in self.statesWithWarning:
            if self.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to cancel?", True, True) == False:
                return
        self.sendPostRequest(printer[0], printer[1], "job", '{ "command": "cancel" }')

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

    def printerFilePrint(self, item, path):
        self.sendPostRequest(item[0], item[1], "files/" + path, '{ "command": "select", "print": true }')

    def setTemperature(self, host, key, what, temp):
        path = "printer/bed"
        s = "{\"command\": \"target\", \"target\": " + temp + "}"

        if "tool" in what:
            path = "printer/tool"
            s = "{\"command\": \"target\", \"targets\": {\"" + what + "\": " + temp + "}}"

        if temp == None:
            temp = 0

        self.sendPostRequest(host, key, path, s)

    def printerHeatTool(self, p):
        self.setTemperature(p[0], p[1], "tool0", p[2])

    def printerHeatBed(self, p):
        self.setTemperature(p[0], p[1], "bed", p[3])

    def printerCooldown(self, p):
        state = self.getState(p[0], p[1])
        if state in self.statesWithWarning:
            if self.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to turn it off?", True, True) == False:
                return

        self.setTemperature(p[0], p[1], "tool0", 0)
        self.setTemperature(p[0], p[1], "bed", 0)

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
        self.settingsWindow.setGeometry(int(x), int(y), int(self.settingsWindow.width()), int(self.settingsWindow.height()) + 50)

    def removeSettingsWindow(self):
        self.settingsWindow = None

    def restartApp(self):
        QCoreApplication.exit(42)

    def closeAll(self):
        for cw in self.camWindows:
            cw.close()

        if self.settingsWindow != None:
            self.settingsWindow.close()

        if self.inSysTray:
            self.trayIcon.setVisible(False)
        else:
            self.mainWindow.setVisible(False)
