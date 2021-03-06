#!/bin/sh

rm -rf build/archlinux
mkdir -p build/archlinux

./build_linux.sh
cp -r build/linux/dist/OctoTray build/archlinux/octotray

cp -r data/* build/archlinux/
cp dist/PKGBUILD build/archlinux/

cd build/archlinux
makepkg

cd ../..
mkdir -p build/dist
cp build/archlinux/OctoTray-*.pkg.* build/dist
