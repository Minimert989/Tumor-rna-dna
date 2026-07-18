from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import project_path
from .db import AtlasDB


def run(cfg: dict[str, Any], db: AtlasDB) -> dict[str, Any]:
    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cancer_types": db.execute("SELECT COUNT(*) FROM cancer_types").fetchone()[0],
        "drug_products": db.execute("SELECT COUNT(*) FROM drug_products").fetchone()[0],
        "drug_approvals": db.execute("SELECT COUNT(*) FROM drug_approvals").fetchone()[0],
        "drug_labels": db.execute("SELECT COUNT(*) FROM drug_labels").fetchone()[0],
        "clinical_trials": db.execute("SELECT COUNT(*) FROM clinical_trials").fetchone()[0],
        "mapped_trials": db.execute("SELECT COUNT(*) FROM clinical_trials WHERE mapped_oncotree_codes <> '[]'").fetchone()[0],
        "biomarker_evidence": db.execute("SELECT COUNT(*) FROM biomarker_therapy_evidence").fetchone()[0],
        "guideline_recommendations": db.execute("SELECT COUNT(*) FROM guideline_recommendations").fetchone()[0],
        "regimen_components": db.execute("SELECT COUNT(*) FROM regimen_components").fetchone()[0],
        "licensed_monographs": db.execute("SELECT COUNT(*) FROM licensed_monographs").fetchone()[0],
        "unresolved_mapping_issues": db.execute("SELECT COUNT(*) FROM mapping_issues WHERE status = 'unresolved'").fetchone()[0],
    }
    report_dir = project_path(cfg, cfg["project"]["report_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "coverage.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    md = ["# All-Cancer Atlas Coverage Audit", ""]
    md.extend(f"- **{k}**: {v}" for k, v in metrics.items())
    md += ["", "## Interpretation", "", "A source count of zero means the corresponding API/export has not been supplied or synchronized. It does not imply no evidence exists."]
    (report_dir / "coverage.md").write_text("\n".join(md), encoding="utf-8")
    return metrics
