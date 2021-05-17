#!/bin/sh

rm -rf build/win
mkdir -p build/win

cp src/* build/win/
cp data/* build/win/
cp dist/setup_win.py build/win/

cd build/win
pyinstaller --noconfirm --onefile --name=OctoTray --windowed --add-data="octotray_icon.png;." octotray.py

cd ../..
mkdir -p build/dist/win
cp -r build/win/dist/* build/dist/win/
