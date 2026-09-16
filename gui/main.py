#!/usr/bin/env python3
"""OpenCraftFormation desktop GUI entrypoint.

Run with:  python main.py
(from a venv with gui/requirements.txt installed)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import webview  # noqa: E402

from app.api import Api  # noqa: E402
from app import paths  # noqa: E402


def resource_path(relative: str) -> str:
    """Resolves paths that work both when run from source and when frozen
    into a PyInstaller onefile bundle (which unpacks to sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return str(Path(base) / relative)


def main() -> None:
    paths.ensure_dirs()
    api = Api()
    webview.create_window(
        "OpenCraftFormation",
        resource_path("web/index.html"),
        js_api=api,
        width=960,
        height=720,
        min_size=(760, 560),
    )
    webview.start()


if __name__ == "__main__":
    main()
