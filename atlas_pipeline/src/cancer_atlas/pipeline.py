from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from .audit import run as audit_run
from .config import project_path
from .db import AtlasDB
from .export import run as export_run
from .http import HttpClient
from .importers import import_eviq, import_monograph, import_nccn
from .mapping import map_trials
from .connectors.base import Context
from .connectors import clinicaltrials, dailymed, drugsatfda, oncokb, oncotree, openfda, rxnorm

console = Console()


def context(cfg: dict[str, Any]) -> tuple[AtlasDB, Context]:
    db = AtlasDB(project_path(cfg, cfg["project"]["database"]), Path(cfg["_project_root"]) / "sql/schema.sql")
    http = HttpClient(
        cfg["project"]["user_agent"],
        timeout=int(cfg["project"].get("request_timeout_seconds", 90)),
        retries=int(cfg["project"].get("max_retries", 5)),
    )
    return db, Context(cfg=cfg, db=db, http=http)


def run_sync(cfg: dict[str, Any], sources: list[str]) -> dict[str, Any]:
    db, ctx = context(cfg)
    result: dict[str, Any] = {}
    try:
        for source in sources:
            console.print(f"[bold cyan]Syncing {source}[/bold cyan]")
            if source == "oncotree": result[source] = oncotree.sync(ctx)
            elif source == "drugs_at_fda": result[source] = drugsatfda.sync(ctx)
            elif source == "openfda_labels": result[source] = openfda.sync(ctx)
            elif source == "dailymed": result[source] = dailymed.sync(ctx)
            elif source == "clinicaltrials": result[source] = clinicaltrials.sync(ctx)
            elif source == "rxnorm": result[source] = rxnorm.sync(ctx)
            elif source == "oncokb_import": result[source] = oncokb.import_annotator_output(ctx)
            else: raise ValueError(f"Unknown source: {source}")
    finally:
        db.close()
    return result


def build(cfg: dict[str, Any]) -> dict[str, Any]:
    db, _ = context(cfg)
    try:
        result = {
            "nccn": import_nccn(cfg, db),
            "eviq": import_eviq(cfg, db),
            "micromedex": import_monograph(cfg, db, "micromedex"),
            "lexidrug": import_monograph(cfg, db, "lexidrug"),
            "oncokb_import": oncokb.import_annotator_output(Context(cfg, db, HttpClient(cfg["project"]["user_agent"]))),
            "trial_mapping": map_trials(cfg, db),
        }
        return result
    finally:
        db.close()


def audit(cfg: dict[str, Any]) -> dict[str, Any]:
    db, _ = context(cfg)
    try:
        return audit_run(cfg, db)
    finally:
        db.close()


def export(cfg: dict[str, Any]) -> Path:
    db, _ = context(cfg)
    try:
        return export_run(cfg, db)
    finally:
        db.close()
