#!/usr/bin/env python
# -*- coding: utf-8 -*-

import py2exe
from distutils.core import setup

APP_NAME = "OctoTray"
APP = [ 'octotray.py' ]
DATA_FILES = [ 'octotray_icon.png' ]
VERSION="0.3"

includes = [
    "PyQt5",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtNetwork",
    "PyQt5.QtWidgets"
]

OPTIONS = {
    "bundle_files": 1,
    "includes": includes
}

setup(
    name=APP_NAME,
    version=VERSION,
    windows=[ { "script": "octotray.py" } ],
    data_files=DATA_FILES,
    options={ 'py2exe': OPTIONS }
)
