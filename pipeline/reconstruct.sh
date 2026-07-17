#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT

python3 - <<'PY'
from __future__ import annotations

import base64
import hashlib
import os
import zipfile
from pathlib import Path

root = Path(os.environ["ROOT"])
parts_dir = root / "pipeline" / "archive_parts"
zip_path = root / "pipeline" / "all_cancer_atlas_pipeline.zip"

parts = sorted(parts_dir.glob("part-*"))
if not parts:
    raise SystemExit(f"No archive parts found under {parts_dir}")

payload = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
try:
    archive = base64.b64decode(payload, validate=True)
except Exception as exc:
    raise SystemExit(f"Invalid base64 archive parts: {exc}") from exc

actual_sha256 = hashlib.sha256(archive).hexdigest()
zip_path.write_bytes(archive)

try:
    with zipfile.ZipFile(zip_path) as zf:
        bad_member = zf.testzip()
        member_count = len(zf.infolist())
except zipfile.BadZipFile as exc:
    raise SystemExit(f"Reconstructed archive is not a valid ZIP: {exc}") from exc

if bad_member is not None:
    raise SystemExit(f"Corrupt ZIP member: {bad_member}")

print(f"Reconstructed {zip_path}")
print(f"SHA256 {actual_sha256}")
print(f"Members {member_count}")
PY
