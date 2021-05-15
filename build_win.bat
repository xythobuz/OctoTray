#!/bin/sh

del build/win
mkdir build/win

cp src/* build/win/
cp data/* build/win/
cp dist/setup_win.py build/win/

cd build/win
python setup_win.py py2exe
