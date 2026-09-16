# Builds the OpenCraftFormation desktop app for Windows into gui\dist\.
# Unsigned build — Windows SmartScreen may warn on first launch; see gui/README.md.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python -m venv .venv-build
. .venv-build\Scripts\Activate.ps1
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

pyinstaller packaging\pyinstaller.spec `
  --distpath dist `
  --workpath build\pyinstaller `
  --noconfirm

deactivate

Write-Host "Build output: gui\dist\OpenCraftFormation\OpenCraftFormation.exe"
