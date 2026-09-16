# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the OpenCraftFormation desktop GUI.
Build with:  pyinstaller packaging/pyinstaller.spec --distpath dist --noconfirm
(run from gui/, with gui/requirements.txt installed — see packaging/build.sh|build.ps1)
"""
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # gui/

if sys.platform == "darwin":
    platform_hidden = ["webview.platforms.cocoa"]
elif sys.platform == "win32":
    platform_hidden = ["webview.platforms.winforms", "webview.platforms.edgechromium"]
else:
    platform_hidden = ["webview.platforms.gtk", "webview.platforms.qt"]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / "web"), "web")],
    hiddenimports=platform_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="OpenCraftFormation",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="OpenCraftFormation.app",
        bundle_identifier="dev.opencraftformation.gui",
    )
