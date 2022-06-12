#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# AspectRatioPixmapLabel.py
#
# see also:
# https://doc.qt.io/qt-5/qtwidgets-widgets-imageviewer-example.html
# https://stackoverflow.com/a/22618496

from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QSize, Qt

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
