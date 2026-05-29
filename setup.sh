#!/usr/bin/env bash
# Set up The Everything Converter on macOS.
# Installs the system tools (via Homebrew) and Python dependencies it relies on.
set -euo pipefail

echo "==> The Everything Converter — macOS setup"

# 1. Homebrew ---------------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is not installed. Install it from https://brew.sh and re-run."
  exit 1
fi

# 2. System tools -----------------------------------------------------------
echo "==> Installing system tools (ffmpeg, pandoc, python-tk)…"
brew install ffmpeg pandoc python-tk || true

echo "==> Installing LibreOffice (used for Office docs & PDF export)…"
brew install --cask libreoffice || true

# 3. Python environment -----------------------------------------------------
PY="${PYTHON:-python3}"
echo "==> Creating virtual environment in .venv (using $PY)…"
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing Python dependencies…"
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

echo
echo "==> Done!"
echo "Activate the environment with:  source .venv/bin/activate"
echo "Launch the GUI with:            ./run.sh"
echo "Or use the CLI:                 everythingconverter --help"
echo "Check installed backends:       everythingconverter doctor"
