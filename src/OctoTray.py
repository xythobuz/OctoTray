#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# OctoTray.py
#
# Main application logic.

import sys
from os import path
from PyQt5 import QtNetwork
from PyQt5.QtWidgets import QSystemTrayIcon, QAction, QMenu, QMessageBox, QDesktopWidget
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices, QCursor
from PyQt5.QtCore import QCoreApplication, QSettings, QUrl
from CamWindow import CamWindow
from SettingsWindow import SettingsWindow
from SettingsWindow import Printer
from MainWindow import MainWindow
from APIOctoprint import APIOctoprint
from APIMoonraker import APIMoonraker

class OctoTray():
    name = "OctoTray"
    vendor = "xythobuz"
    version = "0.5"

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

    # list of Printer objects
    printers = []

    camWindows = []
    settingsWindow = None

    # default, can be overridden in config
    jogMoveSpeedDefault = 10 * 60 # in mm/min
    jogMoveLengthDefault = 10 # in mm

    def __init__(self, app, inSysTray):
        QCoreApplication.setApplicationName(self.name)
        self.app = app
        self.inSysTray = inSysTray

        self.manager = QtNetwork.QNetworkAccessManager()
        self.menu = QMenu()
        self.printers = self.readSettings()

        unknownCount = 0
        for p in self.printers:
            p.menus = []

            if p.apiType.lower() == "octoprint":
                p.api = APIOctoprint(self, p.host, p.key)
            elif p.apiType.lower() == "moonraker":
                p.api = APIMoonraker(self, p.host, p.webcam)
            else:
                print("Unsupported API type " + p.apiType)
                unknownCount += 1
                action = QAction(p.host)
                action.setEnabled(False)
                p.menus.append(action)
                self.menu.addAction(action)
                continue

            commands = p.api.getAvailableCommands()

            # don't populate menu when no methods are available
            if len(commands) == 0:
                unknownCount += 1
                action = QAction(p.host)
                action.setEnabled(False)
                p.menus.append(action)
                self.menu.addAction(action)
                continue

            # top level menu for this printer
            menu = QMenu(p.api.getName())
            p.menus.append(menu)
            self.menu.addMenu(menu)

            # create action for all available commands
            for cmd in commands:
                name, func = cmd
                action = QAction(name)
                action.triggered.connect(lambda chk, n=name, f=func: f(n))
                p.menus.append(action)
                menu.addAction(action)

            if (p.tempTool != None) or (p.tempBed != None):
                menu.addSeparator()

            if p.tempTool != None:
                action = QAction("Preheat Tool")
                action.triggered.connect(lambda chk, p=p: p.api.printerHeatTool(p.tempTool))
                p.menus.append(action)
                menu.addAction(action)

            if p.tempBed != None:
                action = QAction("Preheat Bed")
                action.triggered.connect(lambda chk, p=p: p.api.printerHeatBed(p.tempBed))
                p.menus.append(action)
                menu.addAction(action)

            if (p.tempTool != None) or (p.tempBed != None):
                action = QAction("Cooldown")
                action.triggered.connect(lambda chk, p=p: p.api.printerCooldown())
                p.menus.append(action)
                menu.addAction(action)

            menu.addSeparator()

            fileMenu = QMenu("Recent Files")
            p.menus.append(fileMenu)
            menu.addMenu(fileMenu)

            files = p.api.getRecentFiles(10)
            for f in files:
                fileName, filePath = f
                action = QAction(fileName)
                action.triggered.connect(lambda chk, p=p, f=filePath: p.api.printFile(f))
                p.menus.append(action)
                fileMenu.addAction(action)

            action = QAction("Get Status")
            action.triggered.connect(lambda chk, p=p: p.api.statusDialog())
            p.menus.append(action)
            menu.addAction(action)

            action = QAction("Show Webcam")
            action.triggered.connect(lambda chk, x=p: self.printerWebcamAction(x))
            p.menus.append(action)
            menu.addAction(action)

            action = QAction("Open Web UI")
            action.triggered.connect(lambda chk, x=p: self.printerWebAction(x))
            p.menus.append(action)
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

        printers = []
        l = settings.beginReadArray("printers")
        for i in range(0, l):
            settings.setArrayIndex(i)
            p = Printer()

            # Generic settings
            p.host = settings.value("host", "octopi.local")
            p.apiType = settings.value("api_type", "OctoPrint")
            p.tempTool = settings.value("tool_preheat", "0")
            p.tempBed = settings.value("bed_preheat", "0")
            p.jogSpeed = settings.value("jog_speed", self.jogMoveSpeedDefault)
            p.jogLength = settings.value("jog_length", self.jogMoveLengthDefault)

            # Octoprint specific settings
            p.key = settings.value("key", "")

            # Moonraker specific settings
            p.webcam = settings.value("webcam", "0")

            print("readSettings() " + str(i) + ":\n" + str(p) + "\n")
            printers.append(p)
        settings.endArray()
        return printers

    def writeSettings(self, printers):
        settings = QSettings(self.vendor, self.name)

        settings.remove("printers")
        settings.beginWriteArray("printers")
        for i in range(0, len(printers)):
            p = printers[i]
            print("writeSettings() " + str(i) + ":\n" + str(p) + "\n")

            settings.setArrayIndex(i)

            # Generic settings
            settings.setValue("host", p.host)
            settings.setValue("api_type", p.apiType)
            settings.setValue("tool_preheat", p.tempTool)
            settings.setValue("bed_preheat", p.tempBed)
            settings.setValue("jog_speed", p.jogSpeed)
            settings.setValue("jog_length", p.jogLength)

            # Octoprint specific settings
            settings.setValue("key", p.key)

            # Moonraker specific settings
            settings.setValue("webcam", p.webcam)
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

    def exit(self):
        QCoreApplication.quit()

    def printerWebAction(self, item):
        self.openBrowser(item.host)

    def printerWebcamAction(self, item):
        for cw in self.camWindows:
            if cw.getHost() == item.host:
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
