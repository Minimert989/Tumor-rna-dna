from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from cancer_atlas.util import json_text, run_id
from .base import Context


def _parent_code(item: dict[str, Any]) -> str | None:
    parent = item.get("parent")
    if isinstance(parent, str):
        return parent
    if isinstance(parent, dict):
        return parent.get("code")
    return item.get("parentCode")


def _codes(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out = []
        for x in value:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                out.extend(str(v) for v in x.values() if v)
        return sorted(set(out))
    if isinstance(value, dict):
        return sorted(set(str(v) for v in value.values() if v))
    return [str(value)]


def sync(ctx: Context) -> int:
    source = "oncotree"
    rid = run_id(source)
    started = datetime.now(timezone.utc)
    cfg = ctx.cfg["sources"][source]
    params = {"version": cfg["version"]}
    payload = ctx.http.get_json(cfg["flat_url"], params=params)
    if isinstance(payload, dict) and "tumorTypes" in payload:
        items = payload["tumorTypes"]
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("Unexpected OncoTree response shape")
    rows = []
    for item in items:
        code = item.get("code")
        if not code:
            continue
        rows.append({
            "oncotree_code": code,
            "name": item.get("name"),
            "main_type": item.get("mainType") or item.get("main_type"),
            "tissue": item.get("tissue") or item.get("color"),
            "level": item.get("level"),
            "parent_code": _parent_code(item),
            "nci_codes": json_text(_codes(item.get("nci"))),
            "umls_codes": json_text(_codes(item.get("umls"))),
            "synonyms": json_text(_codes(item.get("externalReferences")) + _codes(item.get("history"))),
            "deprecated": bool(item.get("revocations") or item.get("deprecated", False)),
            "version": cfg["version"],
            "raw_json": json_text(item),
            "source_run_id": rid,
        })
    df = pd.DataFrame(rows)
    ctx.db.upsert_df("cancer_types", df, "oncotree_code")
    ctx.db.execute(
        "INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [rid, source, started, datetime.now(timezone.utc), "completed", cfg["version"], len(items), len(df), cfg["flat_url"], None, None],
    )
    return len(df)
