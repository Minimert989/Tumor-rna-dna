from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from cancer_atlas.util import json_text, run_id, stable_id
from .base import Context


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("data", "spls", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def sync_metadata(ctx: Context) -> int:
    source = "dailymed"
    rid = run_id(source)
    started = datetime.now(timezone.utc)
    cfg = ctx.cfg["sources"][source]
    page = 1
    rows = []
    while True:
        payload = ctx.http.get_json(f'{cfg["base_url"]}/spls.json', params={"page": page, "pagesize": cfg.get("metadata_page_size", 100)})
        items = _items(payload)
        if not items:
            break
        for item in items:
            setid = item.get("setid") or item.get("setId") or item.get("set_id")
            if not setid:
                continue
            rows.append({
                "label_id": stable_id("dailymed", setid, item.get("version")),
                "set_id": setid,
                "version": str(item.get("version") or ""),
                "application_numbers": json_text(item.get("application_number") or []),
                "brand_names": json_text(item.get("title") or item.get("drug_name") or []),
                "generic_names": "[]",
                "active_ingredients": "[]",
                "route": "[]",
                "dosage_form": "[]",
                "indications_and_usage": "",
                "dosage_and_administration": "",
                "contraindications": "",
                "boxed_warning": "",
                "warnings_and_precautions": "",
                "adverse_reactions": "",
                "drug_interactions": "",
                "clinical_studies": "",
                "effective_time": item.get("published_date") or item.get("effective_time"),
                "source": "DailyMed",
                "source_url": f'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}',
                "raw_json": json_text(item),
                "source_run_id": rid,
            })
        if len(items) < cfg.get("metadata_page_size", 100):
            break
        page += 1
    if rows:
        ctx.db.upsert_df("drug_labels", pd.DataFrame(rows), "label_id")
    ctx.db.execute(
        "INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [rid, source, started, datetime.now(timezone.utc), "completed", "v2", len(rows), len(rows), cfg["base_url"], None, None],
    )
    return len(rows)


def sync(ctx: Context) -> int:
    return sync_metadata(ctx)
