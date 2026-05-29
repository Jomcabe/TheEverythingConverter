#!/usr/bin/env bash
# Build a standalone macOS .app and package it into a .dmg.
# Usage:  ./packaging/build_macos.sh
set -euo pipefail
cd "$(dirname "$0")/.."

APP_NAME="The Everything Converter"
PY="${PYTHON:-python3}"

echo "==> Creating build virtualenv (.build-venv)…"
"$PY" -m venv .build-venv
# shellcheck disable=SC1091
source .build-venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt pyinstaller

echo "==> Running PyInstaller…"
rm -rf build dist
pyinstaller packaging/EverythingConverter.spec --noconfirm

APP_PATH="dist/${APP_NAME}.app"
if [ ! -d "$APP_PATH" ]; then
  echo "error: expected app at '$APP_PATH' was not produced." >&2
  exit 1
fi

echo "==> Packaging into a .dmg…"
DMG="dist/EverythingConverter-macOS.dmg"
rm -f "$DMG"
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG"

echo
echo "==> Done!"
echo "App: $APP_PATH"
echo "DMG: $DMG  (this is what you send to friends)"
