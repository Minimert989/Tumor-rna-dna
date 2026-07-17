from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from rapidfuzz import fuzz, process

from .config import project_path
from .db import AtlasDB
from .util import normalize_text, stable_id


def build_dictionary(cfg: dict[str, Any], db: AtlasDB) -> tuple[dict[str, str], list[str]]:
    cancer = db.dataframe("SELECT oncotree_code, name, main_type, synonyms FROM cancer_types")
    mapping: dict[str, str] = {}
    for r in cancer.to_dict("records"):
        for text in [r.get("name"), r.get("main_type")]:
            if text:
                mapping[normalize_text(text)] = r["oncotree_code"]
        try:
            synonyms = json.loads(r.get("synonyms") or "[]")
        except Exception:
            synonyms = []
        for text in synonyms:
            if text:
                mapping[normalize_text(text)] = r["oncotree_code"]
    alias_path = project_path(cfg, cfg["mapping"]["manual_aliases_path"])
    if alias_path.exists():
        aliases = pd.read_csv(alias_path, dtype=str).fillna("")
        for r in aliases.to_dict("records"):
            mapping[normalize_text(r["alias"])] = r["oncotree_code"]
    choices = list(mapping.keys())
    return mapping, choices


def map_name(name: str, mapping: dict[str, str], choices: list[str], threshold: int) -> tuple[str | None, float]:
    norm = normalize_text(name)
    if not norm:
        return None, 0.0
    if norm in mapping:
        return mapping[norm], 100.0
    result = process.extractOne(norm, choices, scorer=fuzz.token_set_ratio)
    if not result:
        return None, 0.0
    choice, score, _ = result
    return (mapping[choice], float(score)) if score >= threshold else (None, float(score))


def map_trials(cfg: dict[str, Any], db: AtlasDB) -> dict[str, int]:
    mapping, choices = build_dictionary(cfg, db)
    threshold = int(cfg["mapping"].get("fuzzy_threshold", 92))
    trials = db.dataframe("SELECT nct_id, conditions FROM clinical_trials")
    mapped = issues = 0
    for r in trials.to_dict("records"):
        try:
            conditions = json.loads(r["conditions"] or "[]")
        except Exception:
            conditions = []
        codes: list[str] = []
        for condition in conditions:
            code, score = map_name(condition, mapping, choices, threshold)
            if code:
                codes.append(code)
            elif cfg["mapping"].get("retain_unmatched", True):
                issue_id = stable_id("trial_condition", r["nct_id"], condition)
                db.execute("DELETE FROM mapping_issues WHERE issue_id = ?", [issue_id])
                db.execute(
                    "INSERT INTO mapping_issues VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [issue_id, "clinical_trial_condition", r["nct_id"], condition, None, score, "unresolved", None, None],
                )
                issues += 1
        if codes:
            db.execute("UPDATE clinical_trials SET mapped_oncotree_codes = ? WHERE nct_id = ?", [json.dumps(sorted(set(codes))), r["nct_id"]])
            mapped += 1
    return {"mapped_trials": mapped, "unmatched_conditions": issues}
