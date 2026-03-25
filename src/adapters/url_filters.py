from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urlparse

GENERIC_NOISE_URL_FRAGMENTS = (
    "/deportes/",
    "/motor/",
    "/tiempo/",
    "/meteorologia/",
    "/el-tiempo/",
    "/aemet/",
    "/loterias/",
    "/horoscopo/",
    "/shopping/",
    "/compras/",
    "/descuentos/",
    "/branded-content/",
    "/brandstudio/",
    "/publi/",
    "/promociones/",
    "/newsletter/",
    "/video/",
)

STATIC_ASSET_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".pdf",
    ".mp4",
    ".mp3",
    ".woff",
    ".woff2",
    ".ttf",
)

_DATE_PATTERNS = (
    re.compile(r"(?<!\d)(20\d{2})/(0[1-9]|1[0-2])/([0-2]\d|3[01])(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})-(0[1-9]|1[0-2])-([0-2]\d|3[01])(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})(0[1-9]|1[0-2])([0-2]\d|3[01])(?!\d)"),
)


def is_probable_noise_url(link: str, *, extra_fragments: tuple[str, ...] = ()) -> bool:
    normalized = link.strip().lower()
    if not normalized:
        return False
    if any(fragment in normalized for fragment in GENERIC_NOISE_URL_FRAGMENTS + extra_fragments):
        return True
    path = urlparse(normalized).path
    return any(path.endswith(ext) for ext in STATIC_ASSET_EXTENSIONS)


def extract_url_date(link: str) -> date | None:
    normalized = link.strip().lower()
    if not normalized:
        return None
    path = urlparse(normalized).path
    for pattern in _DATE_PATTERNS:
        match = pattern.search(path)
        if match is None:
            continue
        try:
            return datetime.strptime("-".join(match.groups()), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def freshness_priority_key(link: str, target_date: str) -> tuple[int, int, str]:
    parsed_target = datetime.strptime(target_date, "%Y-%m-%d").date()
    url_date = extract_url_date(link)
    if url_date is None:
        return (2, 9999, link)
    delta_days = abs((parsed_target - url_date).days)
    if delta_days == 0:
        tier = 0
    elif delta_days <= 2:
        tier = 1
    else:
        tier = 2
    return (tier, delta_days, link)
