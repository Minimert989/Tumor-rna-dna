from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import ijson
import pandas as pd

from cancer_atlas.config import env
from cancer_atlas.util import flatten_text, json_text, run_id, stable_id
from .base import Context

LABEL_FIELDS = [
    "indications_and_usage", "dosage_and_administration", "contraindications",
    "boxed_warning", "warnings_and_precautions", "adverse_reactions",
    "drug_interactions", "clinical_studies"
]


def _urls(node: Any) -> Iterable[str]:
    if isinstance(node, dict):
        for value in node.values():
            yield from _urls(value)
    elif isinstance(node, list):
        for value in node:
            yield from _urls(value)
    elif isinstance(node, str) and node.startswith("http"):
        yield node


def _is_label_partition(url: str) -> bool:
    low = url.lower()
    return "drug" in low and "label" in low and low.endswith(".zip")


def _record_to_row(record: dict[str, Any], rid: str, source_url: str) -> dict[str, Any]:
    ofda = record.get("openfda") or {}
    set_id = record.get("set_id") or record.get("id") or stable_id("openfda_label", source_url, record.get("effective_time"), ofda.get("brand_name"))
    row = {
        "label_id": stable_id("openfda", set_id, record.get("effective_time")),
        "set_id": set_id,
        "version": record.get("version"),
        "application_numbers": json_text(ofda.get("application_number", [])),
        "brand_names": json_text(ofda.get("brand_name", [])),
        "generic_names": json_text(ofda.get("generic_name", [])),
        "active_ingredients": json_text(record.get("active_ingredient") or ofda.get("substance_name", [])),
        "route": json_text(ofda.get("route", [])),
        "dosage_form": json_text(ofda.get("dosage_form", [])),
        "effective_time": record.get("effective_time"),
        "source": "openFDA",
        "source_url": source_url,
        "raw_json": json_text(record),
        "source_run_id": rid,
    }
    for field in LABEL_FIELDS:
        row[field] = flatten_text(record.get(field))
    return row


def _iter_json_zip(zip_path: Path) -> Iterable[dict[str, Any]]:
    with zipfile.ZipFile(zip_path) as z:
        for member in z.namelist():
            if not member.lower().endswith(".json"):
                continue
            with z.open(member) as f:
                try:
                    yield from ijson.items(f, "results.item")
                except Exception:
                    f.seek(0)
                    payload = json.load(f)
                    for record in payload.get("results", []):
                        yield record


def sync_bulk(ctx: Context) -> int:
    source = "openfda_labels"
    rid = run_id(source)
    started = datetime.now(timezone.utc)
    cfg = ctx.cfg["sources"][source]
    manifest = ctx.http.get_json(cfg["bulk_manifest_url"])
    urls = sorted(set(u for u in _urls(manifest) if _is_label_partition(u)))
    if not urls:
        raise RuntimeError("No openFDA drug-label bulk partitions discovered")
    rows = []
    raw_dir = ctx.raw_dir / source
    for i, url in enumerate(urls, 1):
        name = Path(urlparse(url).path).name or f"label-{i}.zip"
        path, _ = ctx.http.download(url, raw_dir / name)
        for record in _iter_json_zip(path):
            rows.append(_record_to_row(record, rid, url))
            if len(rows) >= 10000:
                ctx.db.upsert_df("drug_labels", pd.DataFrame(rows), "label_id")
                rows.clear()
    if rows:
        ctx.db.upsert_df("drug_labels", pd.DataFrame(rows), "label_id")
    count = ctx.db.execute("SELECT COUNT(*) FROM drug_labels WHERE source_run_id = ?", [rid]).fetchone()[0]
    ctx.db.execute(
        "INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [rid, source, started, datetime.now(timezone.utc), "completed", None, count, count, cfg["bulk_manifest_url"], None, None],
    )
    return count


def sync_api(ctx: Context) -> int:
    source = "openfda_labels"
    rid = run_id(source)
    started = datetime.now(timezone.utc)
    cfg = ctx.cfg["sources"][source]
    api_key = env("OPENFDA_API_KEY")
    regex = ctx.cfg["scope"]["oncology_text_regex"]
    terms = ["cancer", "carcinoma", "leukemia", "lymphoma", "myeloma", "sarcoma", "melanoma", "neoplasm"]
    seen = set()
    total = 0
    for term in terms:
        skip = 0
        while True:
            params = {"search": f'indications_and_usage:"{term}"', "limit": cfg.get("page_size", 1000), "skip": skip}
            if api_key:
                params["api_key"] = api_key
            try:
                payload = ctx.http.get_json(cfg["api_url"], params=params)
            except Exception:
                break
            records = payload.get("results", [])
            if not records:
                break
            rows = []
            for record in records:
                row = _record_to_row(record, rid, cfg["api_url"])
                if row["label_id"] in seen:
                    continue
                if not re.search(regex, row["indications_and_usage"] or ""):
                    continue
                seen.add(row["label_id"])
                rows.append(row)
            if rows:
                ctx.db.upsert_df("drug_labels", pd.DataFrame(rows), "label_id")
                total += len(rows)
            if len(records) < cfg.get("page_size", 1000):
                break
            skip += len(records)
    ctx.db.execute(
        "INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [rid, source, started, datetime.now(timezone.utc), "completed", None, total, total, cfg["api_url"], None, None],
    )
    return total


def sync(ctx: Context) -> int:
    mode = ctx.cfg["sources"]["openfda_labels"].get("mode", "bulk")
    return sync_bulk(ctx) if mode == "bulk" else sync_api(ctx)
