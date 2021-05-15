#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

APP = ['octotray.py']
APP_NAME = "OctoTray"
DATA_FILES = ['octotray_icon.png']
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'octotray_icon.png',
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleGetInfoString': "Control OctoPrint instances from system tray",
        'CFBundleIdentifier': "de.xythobuz.octotray",
        'CFBundleVersion': "0.3.0",
        'CFBundleShortVersionString': "0.3.0",
        'NSHumanReadableCopyright': u"Copyright © 2021, Thomas Buck, All Rights Reserved"
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
