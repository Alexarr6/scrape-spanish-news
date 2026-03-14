from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from src.adapters.rss_adapter import GenericRSSAdapter
from src.core.adapter import RunConfig


class ABCAdapter(GenericRSSAdapter):
    source = "abc"
    feeds = [
        "https://www.abc.es/rss/feeds/abc_EspanaEspana.xml",
        "https://www.abc.es/rss/feeds/abc_espana.xml",
        "https://www.abc.es/rss/feeds/abc_Politica.xml",
        "https://www.abc.es/rss/feeds/abc_ultimas_noticias.xml",
    ]
    sitemaps = [
        "https://www.abc.es/sitemap.xml",
        "https://www.abc.es/sitemap-news.xml",
    ]
    html_fallback_pages = [
        "https://www.abc.es/espana/",
        "https://www.abc.es/espana/politica/",
    ]

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()

        # Layer 1: RSS
        for feed in self.feeds:
            try:
                xml = self.http.get_text(feed)
            except Exception:
                continue
            for item in self._parse_feed(xml):
                link = item.get("link", "")
                if self._accept(link, seen):
                    urls.append(link)
                if len(urls) >= cfg.max_discovery_urls:
                    return urls

        # Layer 2: sitemap
        if len(urls) < 25:
            for sm in self.sitemaps:
                try:
                    xml = self.http.get_text(sm)
                except Exception:
                    continue
                for link in self._parse_sitemap(xml):
                    if self._accept(link, seen):
                        urls.append(link)
                    if len(urls) >= cfg.max_discovery_urls:
                        return urls

        # Layer 3: HTML fallback
        if len(urls) < 20:
            for page in self.html_fallback_pages:
                try:
                    html = self.http.get_text(page)
                except Exception:
                    continue
                for link in self._extract_links(html):
                    if self._accept(link, seen):
                        urls.append(link)
                    if len(urls) >= cfg.max_discovery_urls:
                        return urls

        return urls

    def _accept(self, link: str, seen: set[str]) -> bool:
        if not link or link in seen:
            return False
        lo = link.lower()
        allowed = ("/espana/", "/politica/", "/nacional/")
        if not any(k in lo for k in allowed):
            return False
        seen.add(link)
        return True

    def _parse_sitemap(self, xml_text: str) -> list[str]:
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return []
        links = []
        for loc in root.findall(".//{*}loc"):
            if loc.text:
                links.append(loc.text.strip())
        return links

    def _extract_links(self, html: str) -> list[str]:
        out = re.findall(r'href=["\'](https://www\\.abc\\.es[^"\']+)["\']', html)
        return out
