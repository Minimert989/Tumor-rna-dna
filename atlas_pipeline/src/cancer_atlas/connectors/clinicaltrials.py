from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from cancer_atlas.util import flatten_text, json_text, run_id
from .base import Context


def _parse(study: dict[str, Any], rid: str) -> dict[str, Any]:
    p = study.get("protocolSection") or {}
    ident = p.get("identificationModule") or {}
    status = p.get("statusModule") or {}
    design = p.get("designModule") or {}
    cond = p.get("conditionsModule") or {}
    arms = p.get("armsInterventionsModule") or {}
    elig = p.get("eligibilityModule") or {}
    outcomes = p.get("outcomesModule") or {}
    nct = ident.get("nctId")
    return {
        "nct_id": nct,
        "brief_title": ident.get("briefTitle"),
        "official_title": ident.get("officialTitle"),
        "study_type": design.get("studyType"),
        "phases": json_text(design.get("phases", [])),
        "overall_status": status.get("overallStatus"),
        "start_date": ((status.get("startDateStruct") or {}).get("date")),
        "completion_date": ((status.get("completionDateStruct") or {}).get("date")),
        "conditions": json_text(cond.get("conditions", [])),
        "keywords": json_text(cond.get("keywords", [])),
        "interventions": json_text(arms.get("interventions", [])),
        "eligibility": flatten_text(elig.get("eligibilityCriteria")),
        "minimum_age": elig.get("minimumAge"),
        "maximum_age": elig.get("maximumAge"),
        "sex": elig.get("sex"),
        "enrollment": ((design.get("enrollmentInfo") or {}).get("count")),
        "primary_outcomes": json_text(outcomes.get("primaryOutcomes", [])),
        "secondary_outcomes": json_text(outcomes.get("secondaryOutcomes", [])),
        "has_results": bool(study.get("hasResults")),
        "study_url": f"https://clinicaltrials.gov/study/{nct}" if nct else None,
        "mapped_oncotree_codes": "[]",
        "raw_json": json_text(study),
        "source_run_id": rid,
    }


def _queries(ctx: Context) -> list[str]:
    cfg = ctx.cfg["sources"]["clinicaltrials"]
    strategy = cfg.get("query_strategy", "root_terms")
    if strategy == "oncotree":
        names = ctx.db.dataframe(
            """
            SELECT DISTINCT name
            FROM cancer_types
            WHERE COALESCE(deprecated, FALSE) = FALSE
              AND name IS NOT NULL AND length(trim(name)) > 2
              AND COALESCE(level, 0) >= 2
            ORDER BY name
            """
        )["name"].astype(str).tolist()
        queries = names + list(ctx.cfg["scope"]["oncology_condition_queries"])
    else:
        queries = list(ctx.cfg["scope"]["oncology_condition_queries"])
    out, seen = [], set()
    for q in queries:
        key = q.casefold().strip()
        if key and key not in seen:
            out.append(q.strip())
            seen.add(key)
    max_queries = int(cfg.get("max_queries", 0) or 0)
    return out[:max_queries] if max_queries > 0 else out


def sync(ctx: Context) -> int:
    source = "clinicaltrials"
    rid = run_id(source)
    started = datetime.now(timezone.utc)
    cfg = ctx.cfg["sources"][source]
    page_size = int(cfg.get("page_size", 1000))
    raw_dir = ctx.raw_dir / source
    raw_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = raw_dir / "completed_queries.json"
    completed: set[str] = set()
    if cfg.get("resume", True) and checkpoint_path.exists():
        try:
            completed = set(json.loads(checkpoint_path.read_text(encoding="utf-8")))
        except Exception:
            completed = set()
    seen = set(ctx.db.dataframe("SELECT nct_id FROM clinical_trials")["nct_id"].astype(str).tolist())
    written = 0
    queries = _queries(ctx)
    for query_index, query in enumerate(queries, 1):
        if query in completed:
            continue
        token = None
        while True:
            params: dict[str, Any] = {"query.cond": query, "pageSize": page_size, "format": "json"}
            if token:
                params["pageToken"] = token
            payload = ctx.http.get_json(cfg["base_url"], params=params)
            studies = payload.get("studies", [])
            rows = []
            for study in studies:
                nct = (((study.get("protocolSection") or {}).get("identificationModule") or {}).get("nctId"))
                if not nct or nct in seen:
                    continue
                seen.add(nct)
                rows.append(_parse(study, rid))
            if rows:
                ctx.db.upsert_df("clinical_trials", pd.DataFrame(rows), "nct_id")
                written += len(rows)
            token = payload.get("nextPageToken")
            if not token:
                break
        completed.add(query)
        checkpoint_path.write_text(json.dumps(sorted(completed), ensure_ascii=False, indent=2), encoding="utf-8")
    ctx.db.execute(
        "INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [rid, source, started, datetime.now(timezone.utc), "completed", "v2", len(queries), written, cfg["base_url"], None, None],
    )
    return written
