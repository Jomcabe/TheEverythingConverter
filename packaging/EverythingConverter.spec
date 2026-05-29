# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for The Everything Converter.

Builds a windowed, standalone app that bundles Python, all the pure-pip
backends (Pillow, pandas, PyMuPDF, ...) and a static ffmpeg binary (via
imageio-ffmpeg) so audio/video conversion works with zero setup.

Run from the repository root:

    pyinstaller packaging/EverythingConverter.spec --noconfirm

On macOS this produces ``dist/The Everything Converter.app``; on Windows it
produces ``dist/EverythingConverter/EverythingConverter.exe``.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

APP_NAME = "EverythingConverter"
MAC_APP_NAME = "The Everything Converter"

# Repository root (the spec lives in packaging/).
ROOT = Path(SPECPATH).resolve().parent

datas, binaries, hiddenimports = [], [], []

# Packages without robust built-in hooks: collect everything they ship.
for pkg in ("tkinterdnd2", "imageio_ffmpeg"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# Make sure optional backends are pulled in if installed.
hiddenimports += [
    "PIL", "PIL.Image",
    "pandas", "openpyxl", "fitz",
    "pillow_heif", "tabulate", "lxml", "pyarrow",
]

# Use a custom icon if one is present (.icns on mac, .ico on windows).
icon_mac = ROOT / "packaging" / "icon.icns"
icon_win = ROOT / "packaging" / "icon.ico"
icon = None
if sys.platform == "darwin" and icon_mac.exists():
    icon = str(icon_mac)
elif sys.platform.startswith("win") and icon_win.exists():
    icon = str(icon_win)

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,            # windowed app, no terminal
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{MAC_APP_NAME}.app",
        bundle_identifier="com.everythingconverter.app",
        icon=icon,
        info_plist={
            "CFBundleName": MAC_APP_NAME,
            "CFBundleDisplayName": MAC_APP_NAME,
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
        },
    )
