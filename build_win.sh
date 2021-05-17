#!/bin/sh

rm -rf build/win
mkdir -p build/win

cp src/* build/win/
cp data/* build/win/
cp dist/setup_win.py build/win/

cd build/win
python setup_win.py py2exe

cd ../..
mkdir -p build/dist
cp -r build/win/* build/dist/
