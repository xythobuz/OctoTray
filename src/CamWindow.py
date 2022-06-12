#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# CamWindow.py
#
# see also:
# https://doc.qt.io/qt-5/qtwidgets-widgets-imageviewer-example.html
# https://stackoverflow.com/a/22618496

import time
from PyQt5 import QtNetwork
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSlider, QPushButton
from PyQt5.QtGui import QPixmap, QImageReader
from PyQt5.QtCore import QUrl, QTimer, Qt
from AspectRatioPixmapLabel import AspectRatioPixmapLabel

class CamWindow(QWidget):
    reloadDelayDefault = 1000 # in ms
    statusDelayFactor = 2
    reloadOn = True
    sliderFactor = 100

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

        slide = QHBoxLayout()
        box.addLayout(slide, 0)

        self.slideStaticLabel = QLabel("Refresh")
        slide.addWidget(self.slideStaticLabel, 0)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(int(100 / self.sliderFactor))
        self.slider.setMaximum(int(2000 / self.sliderFactor))
        self.slider.setTickInterval(int(100 / self.sliderFactor))
        self.slider.setPageStep(int(100 / self.sliderFactor))
        self.slider.setSingleStep(int(100 / self.sliderFactor))
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setValue(int(self.reloadDelayDefault / self.sliderFactor))
        self.slider.valueChanged.connect(self.sliderChanged)
        slide.addWidget(self.slider, 1)

        self.slideLabel = QLabel(str(self.reloadDelayDefault) + "ms")
        slide.addWidget(self.slideLabel, 0)

        self.img = AspectRatioPixmapLabel()
        self.img.setPixmap(QPixmap(640, 480))
        box.addWidget(self.img, 1)

        self.statusLabel = QLabel("Status: unavailable")
        box.addWidget(self.statusLabel, 0)
        box.setAlignment(self.statusLabel, Qt.AlignHCenter)

        self.method = self.parent.getMethod(self.printer[0], self.printer[1])
        if self.method != "unknown":
            controls_power = QHBoxLayout()
            box.addLayout(controls_power, 0)

            self.turnOnButton = QPushButton("Turn O&n")
            self.turnOnButton.clicked.connect(self.turnOn)
            controls_power.addWidget(self.turnOnButton)

            self.turnOffButton = QPushButton("Turn O&ff")
            self.turnOffButton.clicked.connect(self.turnOff)
            controls_power.addWidget(self.turnOffButton)

        controls_temp = QHBoxLayout()
        box.addLayout(controls_temp, 0)

        self.cooldownButton = QPushButton("&Cooldown")
        self.cooldownButton.clicked.connect(self.cooldown)
        controls_temp.addWidget(self.cooldownButton)

        self.preheatToolButton = QPushButton("Preheat &Tool")
        self.preheatToolButton.clicked.connect(self.preheatTool)
        controls_temp.addWidget(self.preheatToolButton)

        self.preheatBedButton = QPushButton("Preheat &Bed")
        self.preheatBedButton.clicked.connect(self.preheatBed)
        controls_temp.addWidget(self.preheatBedButton)

        controls_home = QHBoxLayout()
        box.addLayout(controls_home, 0)

        self.homeAllButton = QPushButton("Home &All")
        self.homeAllButton.clicked.connect(self.homeAll)
        controls_home.addWidget(self.homeAllButton, 1)

        self.homeXButton = QPushButton("Home &X")
        self.homeXButton.clicked.connect(self.homeX)
        controls_home.addWidget(self.homeXButton, 0)

        self.homeYButton = QPushButton("Home &Y")
        self.homeYButton.clicked.connect(self.homeY)
        controls_home.addWidget(self.homeYButton, 0)

        self.homeZButton = QPushButton("Home &Z")
        self.homeZButton.clicked.connect(self.homeZ)
        controls_home.addWidget(self.homeZButton, 0)

        controls_move = QHBoxLayout()
        box.addLayout(controls_move, 0)

        self.XPButton = QPushButton("X+")
        self.XPButton.clicked.connect(self.moveXP)
        controls_move.addWidget(self.XPButton)

        self.XMButton = QPushButton("X-")
        self.XMButton.clicked.connect(self.moveXM)
        controls_move.addWidget(self.XMButton)

        self.YPButton = QPushButton("Y+")
        self.YPButton.clicked.connect(self.moveYP)
        controls_move.addWidget(self.YPButton)

        self.YMButton = QPushButton("Y-")
        self.YMButton.clicked.connect(self.moveYM)
        controls_move.addWidget(self.YMButton)

        self.ZPButton = QPushButton("Z+")
        self.ZPButton.clicked.connect(self.moveZP)
        controls_move.addWidget(self.ZPButton)

        self.ZMButton = QPushButton("Z-")
        self.ZMButton.clicked.connect(self.moveZM)
        controls_move.addWidget(self.ZMButton)

        controls_job = QHBoxLayout()
        box.addLayout(controls_job, 0)

        self.PauseButton = QPushButton("Pause/Resume")
        self.PauseButton.clicked.connect(self.pauseResume)
        controls_job.addWidget(self.PauseButton)

        self.CancelButton = QPushButton("Cancel Job")
        self.CancelButton.clicked.connect(self.cancelJob)
        controls_job.addWidget(self.CancelButton)

        self.loadImage()
        self.loadStatus()

    def pauseResume(self):
        self.parent.printerPauseResume(self.printer)

    def cancelJob(self):
        self.parent.printerJobCancel(self.printer)

    def moveXP(self):
        self.parent.printerMoveAction(self.printer, "x", int(self.parent.jogMoveLength), True)

    def moveXM(self):
        self.parent.printerMoveAction(self.printer, "x", -1 * int(self.parent.jogMoveLength), True)

    def moveYP(self):
        self.parent.printerMoveAction(self.printer, "y", int(self.parent.jogMoveLength), True)

    def moveYM(self):
        self.parent.printerMoveAction(self.printer, "y", -1 * int(self.parent.jogMoveLength), True)

    def moveZP(self):
        self.parent.printerMoveAction(self.printer, "z", int(self.parent.jogMoveLength), True)

    def moveZM(self):
        self.parent.printerMoveAction(self.printer, "z", -1 * int(self.parent.jogMoveLength), True)

    def homeX(self):
        self.parent.printerHomingAction(self.printer, "x")

    def homeY(self):
        self.parent.printerHomingAction(self.printer, "y")

    def homeZ(self):
        self.parent.printerHomingAction(self.printer, "z")

    def homeAll(self):
        self.parent.printerHomingAction(self.printer, "xyz")

    def turnOn(self):
        if self.method == "psucontrol":
            self.parent.printerOnAction(self.printer)
        elif self.method == "system":
            cmds = self.parent.getSystemCommands(self.printer[0], self.printer[1])
            for cmd in cmds:
                if "on" in cmd:
                    self.parent.setSystemCommand(self.printer[0], self.printer[1], cmd)
                    break

    def turnOff(self):
        if self.method == "psucontrol":
            self.parent.printerOffAction(self.printer)
        elif self.method == "system":
            cmds = self.parent.getSystemCommands(self.printer[0], self.printer[1])
            for cmd in cmds:
                if "off" in cmd:
                    self.parent.setSystemCommand(self.printer[0], self.printer[1], cmd)
                    break

    def cooldown(self):
        self.parent.printerCooldown(self.printer)

    def preheatTool(self):
        self.parent.printerHeatTool(self.printer)

    def preheatBed(self):
        self.parent.printerHeatBed(self.printer)

    def getHost(self):
        return self.host

    def sliderChanged(self):
        self.slideLabel.setText(str(self.slider.value() * self.sliderFactor) + "ms")

    def closeEvent(self, event):
        self.reloadOn = False
        self.url = ""
        self.parent.removeWebcamWindow(self)

    def scheduleLoadImage(self):
        if self.reloadOn:
            QTimer.singleShot(self.slider.value() * self.sliderFactor, self.loadImage)

    def scheduleLoadStatus(self):
        if self.reloadOn:
            QTimer.singleShot(self.slider.value() * self.sliderFactor * self.statusDelayFactor, self.loadStatus)

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
