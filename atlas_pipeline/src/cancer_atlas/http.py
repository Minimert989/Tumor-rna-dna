from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from .util import sha256_file


class HttpClient:
    def __init__(self, user_agent: str, timeout: int = 90, retries: int = 5):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})

    @retry(
        retry=retry_if_exception_type((requests.RequestException, ValueError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1, max=30),
        reraise=True,
    )
    def get_json(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1, max=30),
        reraise=True,
    )
    def download(self, url: str, path: str | Path, headers: dict[str, str] | None = None) -> tuple[Path, str]:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and p.stat().st_size > 0:
            return p, sha256_file(p)
        tmp = p.with_suffix(p.suffix + ".part")
        with self.session.get(url, headers=headers, timeout=self.timeout, stream=True) as response:
            response.raise_for_status()
            with tmp.open("wb") as f:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
        tmp.replace(p)
        return p, sha256_file(p)

    def polite_pause(self, seconds: float = 0.15) -> None:
        time.sleep(seconds)
