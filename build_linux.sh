#!/bin/sh

rm -rf build/linux
mkdir -p build/linux

cp src/* build/linux/
cp data/* build/linux/

cd build/linux
pyinstaller --noconfirm --onefile --name=OctoTray --windowed --add-data="octotray_icon.png:." octotray.py

zip -r OctoTray_Linux.zip dist/*

cd ../..
mkdir -p build/dist/linux
cp -r build/linux/OctoTray_Linux.zip build/dist/linux/
