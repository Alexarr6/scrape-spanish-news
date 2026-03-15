from __future__ import annotations

import random
import re
import time
import urllib.error
import urllib.request


class HttpClient:
    def __init__(self, timeout: int = 15, max_retries: int = 2, backoff_base: float = 0.4):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    def get_text(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SpainNewsScraper/1.0)",
            "Accept": "text/html,application/xml,application/rss+xml;q=0.9,*/*;q=0.8",
        }
        req = urllib.request.Request(url, headers=headers)

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    content_type = resp.headers.get("Content-Type", "")
                    return self._decode_response_text(raw, content_type)
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                sleep = self.backoff_base * (2**attempt) + random.uniform(0.0, 0.2)
                time.sleep(sleep)
        raise RuntimeError(f"Request failed for {url}: {last_error}")

    def _decode_response_text(self, raw: bytes, content_type: str) -> str:
        for encoding in self._candidate_encodings(content_type):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        # hard fallback, never raise for decode issues
        return raw.decode("utf-8", errors="replace")

    def _candidate_encodings(self, content_type: str) -> list[str]:
        candidates: list[str] = []
        m = re.search(r"charset=([\w\-]+)", content_type or "", flags=re.IGNORECASE)
        if m:
            candidates.append(m.group(1).lower())
        candidates.extend(["utf-8", "cp1252", "latin-1"])

        seen = set()
        out = []
        for item in candidates:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out
