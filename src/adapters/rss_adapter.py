from __future__ import annotations

import html
import xml.etree.ElementTree as ET

from src.core.adapter import BaseSourceAdapter, RunConfig
from src.core.http import HttpClient
from src.core.models import Article, parse_any_date_to_utc_iso
from src.core.text_normalization import normalize_text


class GenericRSSAdapter(BaseSourceAdapter):
    source = "generic"
    feeds: list[str] = []

    def __init__(self, http_client: HttpClient | None = None):
        self.http = http_client or HttpClient()

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        for feed in self.feeds:
            try:
                xml = self.http.get_text(feed)
            except Exception:
                continue
            for item in self._parse_feed(xml):
                link = item.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                urls.append(link)
                if len(urls) >= cfg.max_discovery_urls:
                    return urls
        return urls

    def extract(self, url: str) -> dict:
        html_text = self.http.get_text(url)
        return {"url": url, "html": html_text}

    def normalize(self, raw: dict) -> Article:
        page = raw.get("html", "")
        title = _read_meta(page, "og:title") or _read_title(page)
        description = _read_meta(page, "description") or _read_meta(page, "og:description")
        published = _read_meta(page, "article:published_time") or _read_meta(page, "pubdate")
        section = _read_meta(page, "article:section")

        return Article(
            source=self.source,
            title=normalize_text(title),
            url=raw.get("url", ""),
            published_at=parse_any_date_to_utc_iso(published),
            section=normalize_text(section),
            summary=normalize_text(description),
        )

    def _parse_feed(self, xml_text: str) -> list[dict]:
        root = ET.fromstring(xml_text)
        out: list[dict] = []
        for item in root.findall(".//item"):
            out.append(
                {
                    "title": _xml_text(item.find("title")),
                    "link": _xml_text(item.find("link")),
                    "pubDate": _xml_text(item.find("pubDate")),
                }
            )
        return out


def _xml_text(node) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _read_title(page: str) -> str:
    lo = page.lower()
    a = lo.find("<title>")
    b = lo.find("</title>")
    if a == -1 or b == -1 or b <= a:
        return ""
    return html.unescape(page[a + 7 : b]).strip()


def _read_meta(page: str, key: str) -> str:
    lo = page.lower()
    patterns = [
        f'property="{key.lower()}"',
        f'name="{key.lower()}"',
    ]
    for pat in patterns:
        idx = lo.find(pat)
        if idx == -1:
            continue
        chunk = page[idx : idx + 400]
        marker = 'content="'
        m = chunk.lower().find(marker)
        if m == -1:
            continue
        tail = chunk[m + len(marker) :]
        end = tail.find('"')
        if end == -1:
            continue
        return html.unescape(tail[:end])
    return ""
