from __future__ import annotations

import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cancer_atlas.util import run_id, stable_id
from .base import Context


def _read_txt(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", dtype=str, encoding_errors="replace").fillna("")


def _find(extract_dir: Path, pattern: str) -> Path | None:
    rx = re.compile(pattern, re.I)
    for p in extract_dir.rglob("*.txt"):
        if rx.search(p.name):
            return p
    return None


def sync(ctx: Context) -> dict[str, int]:
    source = "drugs_at_fda"
    rid = run_id(source)
    started = datetime.now(timezone.utc)
    cfg = ctx.cfg["sources"][source]
    raw = ctx.raw_dir / source
    zip_path, digest = ctx.http.download(cfg["zip_url"], raw / "drugsatfda.zip")
    extract_dir = raw / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_dir)
    products_path = _find(extract_dir, r"^Products")
    applications_path = _find(extract_dir, r"^Applications\.txt$")
    submissions_path = _find(extract_dir, r"^Submissions")
    docs_path = _find(extract_dir, r"^ApplicationDocs")
    marketing_path = _find(extract_dir, r"^MarketingStatus\.txt$")
    marketing_lookup_path = _find(extract_dir, r"^MarketingStatus_Lookup")
    if not products_path:
        raise FileNotFoundError("Products.txt not found in Drugs@FDA ZIP")
    products = _read_txt(products_path)
    applications = _read_txt(applications_path) if applications_path else pd.DataFrame()
    marketing = _read_txt(marketing_path) if marketing_path else pd.DataFrame()
    marketing_lookup = _read_txt(marketing_lookup_path) if marketing_lookup_path else pd.DataFrame()
    if not applications.empty:
        products = products.merge(applications[["ApplNo", "ApplType"]], on="ApplNo", how="left")
    if not marketing.empty:
        products = products.merge(marketing, on=["ApplNo", "ProductNo"], how="left")
    if not marketing_lookup.empty and "MarketingStatusID" in products.columns:
        products = products.merge(marketing_lookup, on="MarketingStatusID", how="left")
    drug_rows = []
    for r in products.to_dict("records"):
        appl = r.get("ApplNo", "")
        pno = r.get("ProductNo", "")
        drug_rows.append({
            "drug_id": stable_id("drugsfda", appl, pno),
            "canonical_name": r.get("DrugName", ""),
            "active_ingredient": r.get("ActiveIngredient", ""),
            "brand_name": r.get("DrugName", ""),
            "application_number": appl,
            "application_type": r.get("ApplType", ""),
            "product_number": pno,
            "dosage_form": r.get("Form", ""),
            "strength": r.get("Strength", ""),
            "route": "[]",
            "rxnorm_cui": None,
            "marketing_status": r.get("MarketingStatusDescription", r.get("MarketingStatusID", "")),
            "source": "Drugs@FDA",
            "source_record_id": f"{appl}-{pno}",
            "raw_json": r,
            "source_run_id": rid,
        })
    ctx.db.upsert_df("drug_products", pd.DataFrame(drug_rows), "drug_id")
    approval_rows = []
    submissions = _read_txt(submissions_path) if submissions_path else pd.DataFrame()
    docs = _read_txt(docs_path) if docs_path else pd.DataFrame()
    if not submissions.empty:
        if not docs.empty:
            keys = [c for c in ["ApplNo", "SubmissionType", "SubmissionNo"] if c in docs.columns and c in submissions.columns]
            if keys:
                submissions = submissions.merge(docs, on=keys, how="left")
        for r in submissions.to_dict("records"):
            approval_rows.append({
                "approval_id": stable_id("drugsfda_submission", r.get("ApplNo"), r.get("SubmissionType"), r.get("SubmissionNo")),
                "application_number": r.get("ApplNo"),
                "submission_type": r.get("SubmissionType"),
                "submission_number": r.get("SubmissionNo"),
                "action_date": pd.to_datetime(r.get("SubmissionStatusDate"), errors="coerce"),
                "status": r.get("SubmissionStatus"),
                "review_priority": r.get("ReviewPriority"),
                "action_type": r.get("SubmissionClassCodeID"),
                "indication_text": r.get("SubmissionsPublicNotes"),
                "document_url": r.get("ApplicationDocsURL"),
                "source_run_id": rid,
            })
    if approval_rows:
        ctx.db.upsert_df("drug_approvals", pd.DataFrame(approval_rows), "approval_id")
    ctx.db.execute(
        "INSERT INTO source_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [rid, source, started, datetime.now(timezone.utc), "completed", None, len(products), len(drug_rows), str(zip_path), digest, None],
    )
    return {"products": len(drug_rows), "approvals": len(approval_rows)}
