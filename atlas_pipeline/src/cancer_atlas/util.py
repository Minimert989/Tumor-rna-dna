from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Iterable


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def stable_id(*parts: Any) -> str:
    text = "|".join("" if p is None else str(p).strip() for p in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def run_id(source: str) -> str:
    return f"{source}-{uuid.uuid4()}"


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return "\n".join(flatten_text(v) for v in value.values() if v is not None)
    if isinstance(value, (list, tuple, set)):
        return "\n".join(flatten_text(v) for v in value if v is not None)
    return str(value)


def normalize_text(value: Any) -> str:
    text = flatten_text(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("&", " and ").replace("-", " ")
    text = re.sub(r"[^a-z0-9+:/.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def chunks(items: list[Any], size: int) -> Iterable[list[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]
