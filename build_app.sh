#!/bin/bash
# Builds the standalone "Backup Control Center.app" with PyInstaller and
# installs it into /Applications so it can be launched like any other app.
set -euo pipefail
cd "$(dirname "$0")"

source .venv/bin/activate
uv pip install -q pyinstaller

rm -rf build dist
pyinstaller --noconfirm --windowed --name "Backup Control Center" main.py

rm -rf "/Applications/Backup Control Center.app"
cp -R "dist/Backup Control Center.app" /Applications/

echo "Installed: /Applications/Backup Control Center.app"
