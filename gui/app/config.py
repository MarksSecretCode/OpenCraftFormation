"""Local GUI state persistence + params.yaml read/write.

Two separate stores, on purpose:
  - APP_CONFIG_FILE (~/.opencraftformation/config.json): every value on
    Screen 1, restored automatically when the app reopens.
  - params.yaml (repo root): the portable file deploy.sh already reads.
    Written in the same flat key: value format so a human (or the CLI)
    can still edit it directly.
"""
import json
import re
from typing import Any, Dict

from . import paths

BOOL_KEYS = {"whitelist_enabled", "allocate_eip"}
NUMBER_KEYS = {"max_players", "java_memory_mb", "root_volume_size_gb"}
STRING_KEYS = {
    "server_type", "minecraft_version", "seed", "motd", "difficulty",
    "stack_name", "instance_type", "key_name", "ssh_cidr", "region",
    "aws_profile", "vpc_id", "subnet_id",
}
ALL_KEYS = BOOL_KEYS | NUMBER_KEYS | STRING_KEYS

DEFAULTS: Dict[str, Any] = {
    "server_type": "Fabric",
    "minecraft_version": "1.20.1",
    "seed": "",
    "motd": "My hobby server",
    "difficulty": "normal",
    "max_players": 10,
    "java_memory_mb": 3072,
    "whitelist_enabled": False,
    "stack_name": "craftainer",
    "instance_type": "t3.medium",
    "key_name": "",
    "ssh_cidr": "0.0.0.0/0",
    "region": "",
    "aws_profile": "",
    "vpc_id": "",
    "subnet_id": "",
    "allocate_eip": False,
    "root_volume_size_gb": 8,
}

_LINE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$")


def _coerce(key: str, raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        raw = raw[1:-1]
    elif raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        raw = raw[1:-1]
    if key in BOOL_KEYS:
        return raw.strip().lower() == "true"
    if key in NUMBER_KEYS:
        try:
            return int(raw)
        except ValueError:
            return DEFAULTS.get(key, 0)
    return raw


def _strip_comment(line: str) -> str:
    """Strips a trailing # comment, ignoring any # inside a quoted value
    (e.g. motd: "Server #1" must keep the #1)."""
    in_quote = ""
    for i, ch in enumerate(line):
        if in_quote:
            if ch == in_quote:
                in_quote = ""
        elif ch in ("'", '"'):
            in_quote = ch
        elif ch == "#":
            return line[:i]
    return line


def _parse_yaml_flat(path) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = _strip_comment(line)
        if ":" not in line:
            continue
        m = _LINE_RE.match(line.strip())
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        if key in ALL_KEYS:
            values[key] = _coerce(key, value)
    return values


def load_app_config() -> Dict[str, Any]:
    """Restore the last-used form values, falling back to an existing
    params.yaml (so opening the GUI on a repo already configured via the
    CLI picks up its settings), then to DEFAULTS."""
    config = dict(DEFAULTS)
    config.update(_parse_yaml_flat(paths.PARAMS_FILE))
    if paths.APP_CONFIG_FILE.exists():
        try:
            saved = json.loads(paths.APP_CONFIG_FILE.read_text())
            config.update({k: v for k, v in saved.items() if k in ALL_KEYS})
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_app_config(values: Dict[str, Any]) -> None:
    paths.ensure_dirs()
    merged = load_app_config()
    merged.update({k: v for k, v in values.items() if k in ALL_KEYS})
    paths.APP_CONFIG_FILE.write_text(json.dumps(merged, indent=2, sort_keys=True))


def _format_value(key: str, value: Any) -> str:
    if key in BOOL_KEYS:
        return "true" if value else "false"
    if key in NUMBER_KEYS:
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(DEFAULTS.get(key, 0))
    s = "" if value is None else str(value)
    if s == "" or any(c in s for c in (" ", "#", ":", '"')):
        return '"{}"'.format(s.replace('"', '\\"'))
    return s


def write_params_yaml(values: Dict[str, Any]) -> None:
    """Render params.yaml from params.example.yaml's structure, substituting
    real values but keeping the same layout/comments so it's still a
    normal file a human (or the CLI) can read and edit."""
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in values.items() if k in ALL_KEYS})

    template_text = paths.PARAMS_EXAMPLE_FILE.read_text()
    out_lines = [
        "# Written by the OpenCraftFormation GUI. Safe to hand-edit — the",
        "# GUI will preserve any keys it doesn't know about.",
        "",
    ]
    for line in template_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped == "":
            if line.startswith("# Copy this file") or line.startswith("# params.yaml is gitignored"):
                continue
            out_lines.append(line)
            continue
        code, _, comment = line.partition("#")
        m = _LINE_RE.match(code.strip())
        if not m or m.group(1) not in merged:
            out_lines.append(line)
            continue
        key = m.group(1)
        rendered = "{}: {}".format(key, _format_value(key, merged[key]))
        if comment:
            padding = " " * max(1, 30 - len(rendered))
            rendered = "{}{}#{}".format(rendered, padding, comment)
        out_lines.append(rendered)

    paths.PARAMS_FILE.write_text("\n".join(out_lines) + "\n")
