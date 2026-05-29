#!/usr/bin/env bash
# Launch the GUI. Activates the local virtualenv if present.
set -euo pipefail
cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec python -m everythingconverter gui
