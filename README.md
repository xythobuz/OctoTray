# OctoTray Linux Qt client

This is a simple Qt application living in the system tray.
It allows remote-control and observation of 3D printers running OctoPrint.
For the implementation it is using PyQt5.
Automatic builds are provided for Linux, Windows and macOS.

[![Build Distribution Packages](https://github.com/xythobuz/OctoTray/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/xythobuz/OctoTray/actions/workflows/build.yml)

For more [take a look at OctoTray on my website](https://www.xythobuz.de/octotray.html).

If the system tray is not available (or when passing the '-w' parameter) the main menu will instead be shown in a window.

## Building / Running

You have different options of building and running OctoTray:

### From Source

OctoTray can simply be run from the checked out repository, if all dependencies are installed.

    ./src/octotray.py

For this you need Python 3 as well as PyQt5.

### Pre-Built Windows Binary

To run OctoTray on MS Windows without much hassle, a pre-built binary is provided, made with [PyInstaller](https://pyinstaller.readthedocs.io) and GitHub Actions.

Simply download the latest version from the GitHub Actions tab, in the artifacts of the most recent build.
You need to be logged in for this!

You can also find binaries for each release on GitHub.

To create your own binary from source, simply run:

    bash build_win.sh

The resulting executable will be in 'build/dist/win' as well as 'build/dist/OctoTray_Win.zip'.

### Pre-Built macOS Application Bundle

For Mac users, a pre-built application bundle is provided, made with [py2app](https://py2app.readthedocs.io) and GitHub Actions.

Simply download the latest version from the GitHub Actions tab, in the artifacts of the most recent build.
You need to be logged in for this!

You can also find binaries for each release on GitHub.

To create your own bundle from source, simply run:

    ./build_mac.sh

The generated bundle will then be in 'build/mac/dist/OctoTray.app' as well as 'build/dist/OctoTray_Mac.zip'.

### Arch Linux Package

Create and install an Arch Linux package like this:

    ./build_arch.sh
    sudo pacman -U build/dist/octotray-0.3-1-any.pkg.tar.xz

Then run it from your desktop environment menu or even add it to the autostart there.

### Manual Installation on Linux

You can also install the required files manually, which should work for most other Linux distribution and Unices:

    sudo ./build_unix.sh

After logging out and back in, you should find OctoTray in the menu of your graphical desktop environment.
Take a look at the script to see exactly what is installed where.

### Pre-Built Linux Binary

For completeness, a single pre-build Linux binary is also provided on GitHub, made with PyInstaller like the Windows build.
It is however not recommended for productive use.

To create it yourself, simply run:

    ./build_linux.sh

The resulting binary will be in 'build/linux/dist' as well as 'build/dist/OctoTray_Linux.zip'.
