#!/bin/sh

rm -rf build/mac
mkdir -p build/mac

cp -r src/* build/mac/
cp -r data/* build/mac/
cp dist/setup_mac.py build/mac/

cd build/mac
python setup_mac.py py2app

cd dist
zip -r OctoTray_Mac.zip OctoTray.app

cd ../../..
mkdir -p build/dist
cp -r build/mac/dist/OctoTray_Mac.zip build/dist/
