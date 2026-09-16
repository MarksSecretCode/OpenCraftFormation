"""Filesystem locations shared across the GUI backend.

The GUI is a front-end for the existing CLI workflow, not a replacement of
it: it reads and writes the same repo-root params.yaml/overlay/ that
deploy.sh does, so the two stay interchangeable.
"""
from pathlib import Path

# gui/app/paths.py -> gui/app -> gui -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

OVERLAY_DIR = REPO_ROOT / "overlay"
PARAMS_FILE = REPO_ROOT / "params.yaml"
PARAMS_EXAMPLE_FILE = REPO_ROOT / "params.example.yaml"
TEMPLATE_FILE = REPO_ROOT / "template.yaml"
BUILD_DIR = REPO_ROOT / "build"

# Per-user GUI settings (window state, last-used form values) — distinct
# from params.yaml, which is the portable, CLI-compatible config.
APP_DATA_DIR = Path.home() / ".opencraftformation"
APP_CONFIG_FILE = APP_DATA_DIR / "config.json"

OVERLAY_SUBDIRS = {
    "mods": OVERLAY_DIR / "mods",
    "plugins": OVERLAY_DIR / "plugins",
    "config": OVERLAY_DIR / "config",
    "world": OVERLAY_DIR / "world",
}


def ensure_dirs() -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for path in OVERLAY_SUBDIRS.values():
        path.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
