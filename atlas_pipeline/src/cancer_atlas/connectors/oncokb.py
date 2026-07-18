from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from cancer_atlas.config import env, project_path
from cancer_atlas.util import json_text, run_id, stable_id
from .base import Context


def _headers() -> dict[str, str]:
    token = env("ONCOKB_API_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def annotate_variants(ctx: Context, variants_path: str | Path) -> int:
    source = "oncokb"
    rid = run_id(source)
    started = datetime.now(timezone.utc)
    cfg = ctx.cfg["sources"][source]
    token = env("ONCOKB_API_TOKEN")
    if not token:
        raise RuntimeError("ONCOKB_API_TOKEN is required for full OncoKB annotation")
    path = Path(variants_path)
    sep = "\t" if path.suffix.lower() in {".tsv", ".maf", ".txt"} else ","
    df = pd.read_csv(path, sep=sep, dtype=str).fillna("")
    required = {"Hugo_Symbol", "Alteration", "OncoTree_Code"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"OncoKB input is missing columns: {sorted(missing)}")
    rows = []
    for r in df.to_dict("records"):
        params = {
            "hugoSymbol": r["Hugo_Symbol"],
            "alteration": r["Alteration"],
            "tumorType": r["OncoTree_Code"],
            "referenceGenome": r.get("Reference_Genome", "GRCh38"),
        }
        payload = ctx.http.get_json(f'{cfg["base_url"]}/annotate/mutations/byProteinChange', params=params, headers=_headers())
        treatments = payload.get("treatments", []) if isinstance(payload, dict) else []
        if not treatments:
            treatments = [{}]
        for tx in treatments:
            drugs = tx.get("drugs") or []
            therapy = "+".join(d.get("drugName", "") for d in drugs) if isinstance(drugs, list) else str(drugs)
            rows.append({
                "evidence_id": stable_id("oncokb", r["Hugo_Symbol"], r["Alteration"], r["OncoTree_Code"], therapy, tx.get("level")),
                "gene": r["Hugo_Symbol"],
                "alteration": r["Alteration"],
                "biomarker_type": r.get("Biomarker_Type", "mutation"),
                "oncotree_code": r["OncoTree_Code"],
                "therapy": therapy,
                "sensitivity_or_resistance": "resistance" if str(tx.get("level", "")).startswith("R") else "sensitivity",
                "evidence_level": tx.get("level"),
                "fda_level": payload.get("highestFdaLevel") if isinstance(payload, dict) else None,
                "oncogenic": payload.get("oncogenic") if isinstance(payload, dict) else None,
                "mutation_effect": json_text(payload.get("mutationEffect")) if isinstance(payload, dict) else None,
                "citations": json_text(tx.get("pmids") or tx.get("abstracts") or []),
                "source": "OncoKB",
                "source_url": "https://www.oncokb.org/",
                "raw_json": json_text(payload),
                "source_run_id": rid,
            })
    out = pd.DataFrame(rows)
    ctx.db.upsert_df("biomarker_therapy_evidence", out, "evidence_id")
    ctx.db.execute(
        "INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [rid, source, started, datetime.now(timezone.utc), "completed", None, len(df), len(out), str(path), None, None],
    )
    return len(out)


def import_annotator_output(ctx: Context, path: str | Path | None = None) -> int:
    source = "oncokb_annotator"
    rid = run_id(source)
    started = datetime.now(timezone.utc)
    if path is None:
        path = project_path(ctx.cfg, ctx.cfg["licensed_imports"][source]["path"])
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return 0
    df = pd.read_csv(p, sep="\t", dtype=str).fillna("")
    rows = []
    for r in df.to_dict("records"):
        rows.append({
            "evidence_id": stable_id("oncokb_import", r.get("Hugo_Symbol"), r.get("Alteration"), r.get("OncoTree_Code"), r.get("Highest_Level")),
            "gene": r.get("Hugo_Symbol"),
            "alteration": r.get("Alteration"),
            "biomarker_type": "alteration",
            "oncotree_code": r.get("OncoTree_Code"),
            "therapy": r.get("Treatments"),
            "sensitivity_or_resistance": "resistance" if r.get("Highest_Resistance_Level") else "sensitivity",
            "evidence_level": r.get("Highest_Level"),
            "fda_level": r.get("Highest_Sensitive_Level"),
            "oncogenic": r.get("Oncogenic"),
            "mutation_effect": r.get("Mutation_Effect"),
            "citations": json_text([x for x in r.get("Citations", "").split(";") if x]),
            "source": "OncoKB Annotator",
            "source_url": "https://www.oncokb.org/",
            "raw_json": json_text(r),
            "source_run_id": rid,
        })
    out = pd.DataFrame(rows)
    ctx.db.upsert_df("biomarker_therapy_evidence", out, "evidence_id")
    ctx.db.execute(
        "INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [rid, source, started, datetime.now(timezone.utc), "completed", None, len(df), len(out), str(p), None, None],
    )
    return len(out)
