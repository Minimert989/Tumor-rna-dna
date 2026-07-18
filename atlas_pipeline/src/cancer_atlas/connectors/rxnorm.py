from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from cancer_atlas.util import run_id
from .base import Context


def _lookup(ctx: Context, name: str) -> str | None:
    cfg = ctx.cfg["sources"]["rxnorm"]
    payload = ctx.http.get_json(f'{cfg["base_url"]}/rxcui.json', params={"name": name, "search": 2})
    ids = (((payload or {}).get("idGroup") or {}).get("rxnormId") or [])
    return ids[0] if ids else None


def sync(ctx: Context, limit: int | None = None) -> int:
    source = "rxnorm"
    rid = run_id(source)
    started = datetime.now(timezone.utc)
    df = ctx.db.dataframe("SELECT drug_id, COALESCE(NULLIF(active_ingredient,''), canonical_name) AS name FROM drug_products WHERE rxnorm_cui IS NULL OR rxnorm_cui = ''")
    if limit:
        df = df.head(limit)
    updated = 0
    for row in df.itertuples(index=False):
        if not row.name:
            continue
        try:
            rxcui = _lookup(ctx, row.name.split(";")[0].strip())
        except Exception:
            continue
        if rxcui:
            ctx.db.execute("UPDATE drug_products SET rxnorm_cui = ? WHERE drug_id = ?", [rxcui, row.drug_id])
            updated += 1
        ctx.http.polite_pause(0.12)
    ctx.db.execute(
        "INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [rid, source, started, datetime.now(timezone.utc), "completed", None, len(df), updated, ctx.cfg["sources"][source]["base_url"], None, None],
    )
    return updated
