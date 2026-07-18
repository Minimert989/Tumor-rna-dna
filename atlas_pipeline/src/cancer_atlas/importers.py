from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import project_path
from .db import AtlasDB
from .util import run_id, stable_id


def _read(path: Path) -> pd.DataFrame:
    sep = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    return pd.read_csv(path, sep=sep, dtype=str).fillna("")


def import_nccn(cfg, db: AtlasDB, path: str | Path | None = None) -> int:
    rid = run_id("nccn_import")
    started = datetime.now(timezone.utc)
    p = Path(path) if path else project_path(cfg, cfg["licensed_imports"]["nccn"]["path"])
    if not p.exists() or p.stat().st_size == 0:
        return 0
    df = _read(p)
    rows = []
    for r in df.to_dict("records"):
        rows.append({
            "recommendation_id": stable_id("nccn", r.get("source_version"), r.get("oncotree_code"), r.get("stage"), r.get("line_of_therapy"), r.get("regimen_name")),
            "source": r.get("source", "NCCN"),
            "source_version": r.get("source_version"),
            "cancer_name": r.get("cancer_name"),
            "oncotree_code": r.get("oncotree_code"),
            "stage": r.get("stage"),
            "setting": r.get("setting"),
            "line_of_therapy": r.get("line_of_therapy"),
            "biomarker": r.get("biomarker"),
            "regimen_name": r.get("regimen_name"),
            "recommendation_category": r.get("recommendation_category"),
            "preferred_flag": str(r.get("preferred_flag", "")).lower() in {"1", "true", "yes", "y"},
            "source_page": r.get("source_page"),
            "source_url": r.get("source_url"),
            "reviewed_by": r.get("reviewed_by"),
            "reviewed_date": pd.to_datetime(r.get("reviewed_date"), errors="coerce"),
            "notes": r.get("notes"),
            "source_run_id": rid,
        })
    out = pd.DataFrame(rows)
    db.upsert_df("guideline_recommendations", out, "recommendation_id")
    db.execute("INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [rid, "nccn_import", started, datetime.now(timezone.utc), "completed", None, len(df), len(out), str(p), None, None])
    return len(out)


def import_eviq(cfg, db: AtlasDB, path: str | Path | None = None) -> int:
    rid = run_id("eviq_import")
    started = datetime.now(timezone.utc)
    p = Path(path) if path else project_path(cfg, cfg["licensed_imports"]["eviq"]["path"])
    if not p.exists() or p.stat().st_size == 0:
        return 0
    df = _read(p)
    rows = []
    for r in df.to_dict("records"):
        rows.append({
            "regimen_component_id": stable_id("eviq", r.get("protocol_id"), r.get("protocol_version"), r.get("component_drug"), r.get("day_pattern")),
            "source": r.get("source", "eviQ"), "protocol_id": r.get("protocol_id"), "protocol_version": r.get("protocol_version"),
            "cancer_name": r.get("cancer_name"), "oncotree_code": r.get("oncotree_code"), "regimen_name": r.get("regimen_name"),
            "component_drug": r.get("component_drug"), "rxnorm_cui": None, "dose": r.get("dose"), "dose_unit": r.get("dose_unit"),
            "route": r.get("route"), "day_pattern": r.get("day_pattern"), "cycle_days": pd.to_numeric(r.get("cycle_days"), errors="coerce"),
            "total_cycles": r.get("total_cycles"), "premedication": r.get("premedication"), "monitoring": r.get("monitoring"),
            "dose_modification": r.get("dose_modification"), "major_toxicities": r.get("major_toxicities"), "source_url": r.get("source_url"),
            "reviewed_date": pd.to_datetime(r.get("reviewed_date"), errors="coerce"), "source_run_id": rid,
        })
    out = pd.DataFrame(rows)
    db.upsert_df("regimen_components", out, "regimen_component_id")
    db.execute("INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [rid, "eviq_import", started, datetime.now(timezone.utc), "completed", None, len(df), len(out), str(p), None, None])
    return len(out)


def import_monograph(cfg, db: AtlasDB, source: str, path: str | Path | None = None) -> int:
    key = source.lower()
    rid = run_id(f"{key}_import")
    started = datetime.now(timezone.utc)
    p = Path(path) if path else project_path(cfg, cfg["licensed_imports"][key]["path"])
    if not p.exists() or p.stat().st_size == 0:
        return 0
    df = _read(p)
    rows = []
    for r in df.to_dict("records"):
        rows.append({
            "monograph_id": stable_id(key, r.get("source_record_id"), r.get("drug_name"), r.get("export_date")),
            "source": r.get("source", source), "export_date": pd.to_datetime(r.get("export_date"), errors="coerce"),
            "drug_name": r.get("drug_name"), "rxnorm_cui": r.get("rxnorm_cui"), "mechanism": r.get("mechanism"),
            "indications": r.get("indications") or r.get("oncology_uses"), "dosage": r.get("dosage"), "administration": r.get("administration"),
            "contraindications": r.get("contraindications"), "warnings": r.get("warnings"), "adverse_reactions": r.get("adverse_reactions"),
            "drug_interactions": r.get("drug_interactions"), "renal_adjustment": r.get("renal_adjustment"),
            "hepatic_adjustment": r.get("hepatic_adjustment"), "monitoring": r.get("monitoring"), "source_record_id": r.get("source_record_id"),
            "reviewed_date": pd.to_datetime(r.get("reviewed_date"), errors="coerce"), "source_run_id": rid,
        })
    out = pd.DataFrame(rows)
    db.upsert_df("licensed_monographs", out, "monograph_id")
    db.execute("INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [rid, f"{key}_import", started, datetime.now(timezone.utc), "completed", None, len(df), len(out), str(p), None, None])
    return len(out)
