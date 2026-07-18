from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cancer_atlas.config import project_path
from cancer_atlas.db import AtlasDB
from cancer_atlas.http import HttpClient


@dataclass
class Context:
    cfg: dict[str, Any]
    db: AtlasDB
    http: HttpClient

    @property
    def raw_dir(self) -> Path:
        return project_path(self.cfg, self.cfg["project"]["raw_dir"])

    @property
    def staged_dir(self) -> Path:
        return project_path(self.cfg, self.cfg["project"]["staged_dir"])
