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

        self.url = self.printer.api.getWebcamURL()
        print("Webcam: " + self.url)

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

        self.method = self.printer.api.getMethod()
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
        self.printer.api.callPauseResume()

    def cancelJob(self):
        self.printer.api.callJobCancel()

    def moveXP(self):
        self.printer.api.callMove("x", int(self.printer.jogLength), int(self.printer.jogSpeed), True)

    def moveXM(self):
        self.printer.api.callMove("x", -1 * int(self.printer.jogLength), int(self.printer.jogSpeed), True)

    def moveYP(self):
        self.printer.api.callMove("y", int(self.printer.jogLength), int(self.printer.jogSpeed), True)

    def moveYM(self):
        self.printer.api.callMove("y", -1 * int(self.printer.jogLength), int(self.printer.jogSpeed), True)

    def moveZP(self):
        self.printer.api.callMove("z", int(self.printer.jogLength), int(self.printer.jogSpeed), True)

    def moveZM(self):
        self.printer.api.callMove("z", -1 * int(self.printer.jogLength), int(self.printer.jogSpeed), True)

    def homeX(self):
        self.printer.api.callHoming("x")

    def homeY(self):
        self.printer.api.callHoming("y")

    def homeZ(self):
        self.printer.api.callHoming("z")

    def homeAll(self):
        self.printer.api.callHoming("xyz")

    def turnOn(self):
        self.printer.api.turnOn()

    def turnOff(self):
        self.printer.api.turnOff()

    def cooldown(self):
        self.printer.api.printerCooldown()

    def preheatTool(self):
        self.printer.api.printerHeatTool(self.printer.tempTool)

    def preheatBed(self):
        self.printer.api.printerHeatBed(self.printer.tempBed)

    def getHost(self):
        return self.printer.host

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
        t = self.printer.api.getTemperatureString()
        if len(t) > 0:
            s += t
        else:
            s += "Unknown"

        s += " - "

        p = self.printer.api.getProgressString()
        if len(p) > 0:
            s += p
        else:
            s += "Unknown"

        self.statusLabel.setText(s)
        self.scheduleLoadStatus()

    def handleResponse(self, reply):
        if reply.url().url() != self.url:
            print("Reponse for unknown resource: " + reply.url().url())
            return

        if reply.error() != QtNetwork.QNetworkReply.NoError:
            print("Error loading image: " + reply.errorString())
            return

        reader = QImageReader(reply)
        reader.setAutoTransform(True)
        image = reader.read()
        if image == None:
            print("Error decoding image: " + reader.errorString())
            return

        if image.colorSpace().isValid():
            image.convertToColorSpace(QColorSpace.SRgb)
        self.img.setPixmap(QPixmap.fromImage(image))
        self.scheduleLoadImage()
