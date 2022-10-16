#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

APP_NAME = "OctoTray"
APP = [ 'main.py' ]
DATA_FILES = [ 'octotray_icon.png' ]
VERSION="0.5.0"

OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'octotray_icon.png',
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleGetInfoString': "Control OctoPrint/Moonraker instances from system tray",
        'CFBundleIdentifier': "de.xythobuz.octotray",
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'NSHumanReadableCopyright': u"Copyright © 2021 - 2022, Thomas Buck, All Rights Reserved"
    }
}

setup(
    name=APP_NAME,
    version=VERSION,
    app=APP,
    data_files=DATA_FILES,
    options={ 'py2app': OPTIONS },
    setup_requires=[ 'py2app' ]
)
