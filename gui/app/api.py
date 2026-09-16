"""The single object exposed to the web frontend as `pywebview.api`.
Every method here is callable from JS; return values must be JSON-safe.

The GUI never deploys anything itself — it prepares params.yaml and
overlay/, bundles them for CloudShell (see export.py), and shows the
steps to run there. No AWS credentials are required to use the GUI.
"""
import re
from typing import Any, Dict, List

import webview

from . import config, export, hints, overlay, paths

MC_VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")
CIDR_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$")


class Api:
    # ---- Screen 1: config ---------------------------------------------
    def get_config(self) -> Dict[str, Any]:
        paths.ensure_dirs()
        return config.load_app_config()

    def save_config(self, values: Dict[str, Any]) -> Dict[str, Any]:
        errors = self.validate_config(values)
        if errors:
            return {"ok": False, "errors": errors}
        config.save_app_config(values)
        merged = config.load_app_config()
        config.write_params_yaml(merged)
        return {"ok": True}

    def validate_config(self, values: Dict[str, Any]) -> Dict[str, str]:
        errors: Dict[str, str] = {}
        if values.get("server_type") not in ("Forge", "Fabric", "Paper"):
            errors["server_type"] = "Choose Forge, Fabric, or Paper."
        if not MC_VERSION_RE.match(str(values.get("minecraft_version", ""))):
            errors["minecraft_version"] = "Use a version like 1.20.1."
        try:
            if int(values.get("max_players", 0)) < 1:
                errors["max_players"] = "Must be at least 1."
        except (TypeError, ValueError):
            errors["max_players"] = "Must be a number."
        try:
            if int(values.get("java_memory_mb", 0)) < 512:
                errors["java_memory_mb"] = "Must be at least 512."
        except (TypeError, ValueError):
            errors["java_memory_mb"] = "Must be a number."
        try:
            if int(values.get("root_volume_size_gb", 0)) < 8:
                errors["root_volume_size_gb"] = "Must be at least 8 GB."
        except (TypeError, ValueError):
            errors["root_volume_size_gb"] = "Must be a number."
        ssh_cidr = values.get("ssh_cidr", "")
        if ssh_cidr and not CIDR_RE.match(ssh_cidr):
            errors["ssh_cidr"] = "Use CIDR notation, e.g. 203.0.113.5/32."
        if not values.get("stack_name"):
            errors["stack_name"] = "Required."
        return errors

    # ---- Screen 1: reference data (no AWS account access needed) -------
    def instance_type_options(self) -> List[Dict[str, Any]]:
        return hints.instance_type_options()

    def estimate_cost(self, instance_type: str, root_volume_size_gb: int) -> Dict[str, Any]:
        return hints.estimate_monthly_cost(instance_type, root_volume_size_gb)

    def common_regions(self) -> List[str]:
        return hints.COMMON_REGIONS

    def my_public_ip(self) -> Dict[str, Any]:
        try:
            return {"ok": True, "ip": hints.my_public_ip()}
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI as-is
            return {"ok": False, "error": str(exc)}

    # ---- Screen 2: mods/plugins -----------------------------------------
    def list_mods(self, server_type: str) -> List[Dict[str, Any]]:
        return overlay.list_mods(server_type)

    def add_mods(self, server_type: str, file_paths: List[str]) -> Dict[str, Any]:
        return overlay.add_mods(server_type, file_paths)

    def browse_mods(self, server_type: str) -> Dict[str, Any]:
        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=True, file_types=("Jar files (*.jar)", "All files (*.*)")
        )
        if not result:
            return {"added": [], "errors": [], "files": overlay.list_mods(server_type)}
        return overlay.add_mods(server_type, list(result))

    def remove_mod(self, server_type: str, filename: str) -> List[Dict[str, Any]]:
        return overlay.remove_mod(server_type, filename)

    def open_mods_folder(self, server_type: str) -> None:
        overlay.open_mods_folder(server_type)

    def open_world_folder(self) -> None:
        overlay.open_world_folder()

    def open_config_folder(self) -> None:
        overlay.open_config_folder()

    def world_file_count(self) -> int:
        return overlay.world_file_count()

    def special_files_status(self) -> Dict[str, Dict[str, Any]]:
        return overlay.special_files_status()

    def browse_special_file(self, name: str) -> Dict[str, Dict[str, Any]]:
        window = webview.windows[0]
        result = window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False)
        if not result:
            return overlay.special_files_status()
        return overlay.set_special_file(name, result[0])

    def remove_special_file(self, name: str) -> Dict[str, Dict[str, Any]]:
        return overlay.remove_special_file(name)

    # ---- Screen 3: export for CloudShell ---------------------------------
    def build_export(self, values: Dict[str, Any]) -> Dict[str, Any]:
        errors = self.validate_config(values)
        if errors:
            return {"ok": False, "errors": errors}
        config.save_app_config(values)
        merged = config.load_app_config()
        config.write_params_yaml(merged)
        try:
            result = export.build_bundle()
            result["instructions"] = export.cloudshell_instructions()
            return {"ok": True, **result}
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI as-is
            return {"ok": False, "error": str(exc)}

    def open_build_folder(self) -> None:
        export.open_build_folder()
