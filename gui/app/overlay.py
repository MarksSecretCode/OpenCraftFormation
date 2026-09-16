"""Manages the contents of overlay/ — the folder that gets zipped and
copied onto the server as-is. Screen 2 of the GUI is a thin front-end for
this module."""
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from . import paths

SPECIAL_FILES = {"whitelist.json", "ops.json", "server-icon.png"}


def mods_dir_for(server_type: str) -> Path:
    return paths.OVERLAY_SUBDIRS["plugins"] if server_type == "Paper" else paths.OVERLAY_SUBDIRS["mods"]


def _list_dir(dir_path: Path) -> List[Dict[str, Any]]:
    if not dir_path.exists():
        return []
    entries = []
    for p in sorted(dir_path.iterdir()):
        if p.name == ".gitkeep" or p.name.startswith("."):
            continue
        if p.is_file():
            entries.append({"name": p.name, "size": p.stat().st_size})
    return entries


def list_mods(server_type: str) -> List[Dict[str, Any]]:
    return _list_dir(mods_dir_for(server_type))


def add_mods(server_type: str, source_paths: List[str]) -> Dict[str, Any]:
    dest = mods_dir_for(server_type)
    dest.mkdir(parents=True, exist_ok=True)
    added, errors = [], []
    for src in source_paths:
        src_path = Path(src)
        if not src_path.exists():
            errors.append({"name": src_path.name, "reason": "file not found"})
            continue
        if src_path.suffix.lower() != ".jar":
            errors.append({"name": src_path.name, "reason": "not a .jar file"})
            continue
        try:
            shutil.copy2(src_path, dest / src_path.name)
            added.append(src_path.name)
        except OSError as exc:
            errors.append({"name": src_path.name, "reason": str(exc)})
    return {"added": added, "errors": errors, "files": list_mods(server_type)}


def remove_mod(server_type: str, filename: str) -> List[Dict[str, Any]]:
    target = mods_dir_for(server_type) / Path(filename).name
    if target.exists() and target.is_file():
        target.unlink()
    return list_mods(server_type)


def open_mods_folder(server_type: str) -> None:
    open_in_file_manager(mods_dir_for(server_type))


def open_world_folder() -> None:
    open_in_file_manager(paths.OVERLAY_SUBDIRS["world"])


def open_config_folder() -> None:
    open_in_file_manager(paths.OVERLAY_SUBDIRS["config"])


def world_file_count() -> int:
    world_dir = paths.OVERLAY_SUBDIRS["world"]
    if not world_dir.exists():
        return 0
    return sum(1 for p in world_dir.rglob("*") if p.is_file() and p.name != ".gitkeep")


def special_files_status() -> Dict[str, Dict[str, Any]]:
    status = {}
    for name in SPECIAL_FILES:
        p = paths.OVERLAY_DIR / name
        status[name] = {"present": p.exists(), "size": p.stat().st_size if p.exists() else 0}
    return status


def set_special_file(name: str, source_path: str) -> Dict[str, Dict[str, Any]]:
    if name not in SPECIAL_FILES:
        raise ValueError("unknown overlay file: {}".format(name))
    src_path = Path(source_path)
    if not src_path.exists():
        raise FileNotFoundError(source_path)
    paths.OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, paths.OVERLAY_DIR / name)
    return special_files_status()


def remove_special_file(name: str) -> Dict[str, Dict[str, Any]]:
    if name not in SPECIAL_FILES:
        raise ValueError("unknown overlay file: {}".format(name))
    p = paths.OVERLAY_DIR / name
    if p.exists():
        p.unlink()
    return special_files_status()


def open_in_file_manager(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", str(path)])
    elif system == "Windows":
        subprocess.Popen(["explorer", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
