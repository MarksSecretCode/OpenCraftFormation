#!/usr/bin/env bash
# Builds the OpenCraftFormation desktop app for the current OS (macOS/Linux)
# into gui/dist/. Unsigned build — macOS Gatekeeper and Linux distros may
# warn on first launch; see gui/README.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 -m venv .venv-build
# shellcheck disable=SC1091
source .venv-build/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

pyinstaller packaging/pyinstaller.spec \
  --distpath dist \
  --workpath build/pyinstaller \
  --noconfirm

deactivate

if [ -d "dist/OpenCraftFormation.app" ]; then
  echo "Build output: gui/dist/OpenCraftFormation.app"
  echo "(Optional: wrap it in a .dmg with 'hdiutil create -volname OpenCraftFormation -srcfolder dist/OpenCraftFormation.app -ov -format UDZO dist/OpenCraftFormation.dmg')"
else
  echo "Build output: gui/dist/OpenCraftFormation"
fi
