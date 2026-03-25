from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


@dataclass
class Article:
    source: str
    title: str
    url: str
    published_at: str
    section: str = ""
    author: str = ""
    summary: str = ""
    article_text: str = ""
    tags: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def parse_any_date_to_utc_iso(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    raw = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass

    fmts = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    return ""


def iso_to_local_date(value: str, timezone_name: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    raw = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def parse_any_date_to_local_date(value: str, timezone_name: str) -> str:
    iso = parse_any_date_to_utc_iso(value)
    if not iso:
        return ""
    return iso_to_local_date(iso, timezone_name)
