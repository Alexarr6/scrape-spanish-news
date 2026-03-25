from __future__ import annotations

import html
import json
import re
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
            article_text=_read_article_text(page),
            tags=_read_tags(page),
        )

    def _discover_links_from_feeds(self, feeds: list[str]) -> tuple[list[str], int]:
        links: list[str] = []
        errors = 0
        for feed in feeds:
            try:
                xml = self.http.get_text(feed)
            except Exception:
                errors += 1
                continue
            for item in self._parse_feed(xml):
                link = item.get("link", "")
                if link:
                    links.append(link)
        return links, errors

    def _discover_links_from_sitemaps(self, sitemaps: list[str]) -> tuple[list[str], int]:
        links: list[str] = []
        errors = 0
        for sitemap in sitemaps:
            try:
                xml = self.http.get_text(sitemap)
            except Exception:
                errors += 1
                continue
            links.extend(self._parse_sitemap(xml))
        return links, errors

    def _discover_links_from_html_pages(self, pages: list[str]) -> tuple[list[str], int]:
        links: list[str] = []
        errors = 0
        for page in pages:
            try:
                html = self.http.get_text(page)
            except Exception:
                errors += 1
                continue
            links.extend(self._extract_links(html))
        return links, errors

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

    def _parse_sitemap(self, xml_text: str) -> list[str]:
        return _parse_sitemap(xml_text)

    def _extract_links(self, html: str) -> list[str]:
        return _extract_links(html)


def _xml_text(node) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _read_article_text(page: str) -> str:
    for value in _extract_json_ld_values(page, "articleBody"):
        text = normalize_text(value)
        if text:
            return text
    return ""


def _read_tags(page: str) -> str:
    explicit_tags = _split_tag_values(_read_all_meta(page, "article:tag"))
    if explicit_tags:
        return ", ".join(explicit_tags)

    keyword_tags = _split_tag_values(
        _read_all_meta(page, "news_keywords") or _read_all_meta(page, "keywords")
    )
    if keyword_tags:
        return ", ".join(keyword_tags)

    return ""


def _split_tag_values(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for piece in raw.split(","):
            tag = normalize_text(piece)
            key = tag.casefold()
            if not tag or key in seen:
                continue
            seen.add(key)
            out.append(tag)
    return out


def _extract_json_ld_values(page: str, key: str) -> list[str]:
    out: list[str] = []
    for match in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        page,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        blob = html.unescape(match.group(1)).strip()
        if not blob:
            continue
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            continue
        _collect_json_ld_values(payload, key, out)
    return out


def _collect_json_ld_values(payload, key: str, out: list[str]) -> None:
    if isinstance(payload, dict):
        for current_key, value in payload.items():
            if current_key == key and isinstance(value, str):
                out.append(value)
            else:
                _collect_json_ld_values(value, key, out)
    elif isinstance(payload, list):
        for item in payload:
            _collect_json_ld_values(item, key, out)


def _read_title(page: str) -> str:
    lo = page.lower()
    a = lo.find("<title>")
    b = lo.find("</title>")
    if a == -1 or b == -1 or b <= a:
        return ""
    return html.unescape(page[a + 7 : b]).strip()


def _read_meta(page: str, key: str) -> str:
    values = _read_all_meta(page, key)
    return values[0] if values else ""


def _read_all_meta(page: str, key: str) -> list[str]:
    out: list[str] = []
    target = key.casefold()
    for tag in re.finditer(r"<meta\b[^>]*>", page, flags=re.IGNORECASE):
        attrs = tag.group(0)
        prop = re.search(r'(?:property|name)=["\']([^"\']+)["\']', attrs, flags=re.IGNORECASE)
        if prop is None or prop.group(1).casefold() != target:
            continue
        content = re.search(r'content=["\']([^"\']*)["\']', attrs, flags=re.IGNORECASE)
        if content is None:
            continue
        out.append(html.unescape(content.group(1)))
    return out


def _parse_sitemap(xml_text: str) -> list[str]:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []
    links = []
    for loc in root.findall(".//{*}loc"):
        if loc.text:
            links.append(loc.text.strip())
    return links


def _extract_links(html: str) -> list[str]:
    return re.findall(r'href=["\'](https?://[^"\']+)["\']', html)


def _parse_sitemap(xml_text: str) -> list[str]:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []
    links = []
    for loc in root.findall(".//{*}loc"):
        if loc.text:
            links.append(loc.text.strip())
    return links


def _extract_links(html: str) -> list[str]:
    return re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
