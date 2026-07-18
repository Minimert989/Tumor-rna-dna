from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    data["_config_path"] = str(p)
    data["_project_root"] = str(p.parent.parent)
    return data


def project_path(cfg: dict[str, Any], value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return Path(cfg["_project_root"]) / path


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)
