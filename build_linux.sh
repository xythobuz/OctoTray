#!/bin/sh

rm -rf build/linux
mkdir -p build/linux

cp src/* build/linux/
cp data/* build/linux/

cd build/linux
pyinstaller --noconfirm --onefile --name=OctoTray --add-data="octotray_icon.png:." octotray.py

cd dist
zip -r OctoTray_Linux.zip *

cd ../../..
mkdir -p build/dist
cp -r build/linux/dist/OctoTray_Linux.zip build/dist
