#!/bin/bash
# Builds "Backup Control Center.app" with PyInstaller and installs it into /Applications.
set -euo pipefail
cd "$(dirname "$0")"

source .venv/bin/activate
uv pip install -q pyinstaller

rm -rf build dist

# A frozen bundle has no .git, so record the build it was made from.
python scripts/stamp_version.py

pyinstaller --noconfirm --windowed --name "Backup Control Center" \
  --icon assets/icon.icns \
  --add-data "VERSION:." \
  --add-data "_build_info.json:." \
  main.py

rm -rf "/Applications/Backup Control Center.app"
cp -R "dist/Backup Control Center.app" /Applications/
touch "/Applications/Backup Control Center.app"  # nudge Finder/Dock to refresh the cached icon

echo "Installed: /Applications/Backup Control Center.app"

# Remove build artifacts so Spotlight doesn't index a second copy of the .app.
rm -rf build dist
