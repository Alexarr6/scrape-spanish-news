from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from src.adapters.rss_adapter import GenericRSSAdapter
from src.core.adapter import RunConfig


class Minutos20Adapter(GenericRSSAdapter):
    source = "20minutos"
    # Prioridad: España/política/nacional relacionadas.
    feeds = [
        "https://www.20minutos.es/rss/",
        "https://www.20minutos.es/rss/nacional/",
        "https://www.20minutos.es/rss/actualidad/",
    ]
    # Capa intermedia opcional: pueden existir o no según momento editorial.
    sitemaps = [
        "https://www.20minutos.es/sitemap-noticias.xml",
        "https://www.20minutos.es/sitemap-news.xml",
        "https://www.20minutos.es/sitemap.xml",
    ]
    html_fallback_pages = [
        "https://www.20minutos.es/nacional/",
        "https://www.20minutos.es/minuteca/politica/",
        "https://www.20minutos.es/minuteca/espana/",
    ]

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()

        # Layer 1: RSS (hasta 3 endpoints)
        for feed in self.feeds[:3]:
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

        # Layer 2: sitemap (hasta 3 endpoints)
        if len(urls) < 25:
            for sm in self.sitemaps[:3]:
                try:
                    xml = self.http.get_text(sm)
                except Exception:
                    continue
                for link in self._parse_sitemap(xml):
                    if self._accept(link, seen):
                        urls.append(link)
                    if len(urls) >= cfg.max_discovery_urls:
                        return urls

        # Layer 3: HTML fallback (hasta 3 páginas)
        if len(urls) < 20:
            for page in self.html_fallback_pages[:3]:
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
        if "20minutos.es" not in lo:
            return False
        allowed = (
            "/nacional/",
            "/politica/",
            "/espana/",
            "/elecciones",
        )
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
        return re.findall(r'href=["\'](https://www\.20minutos\.es[^"\']+)["\']', html)
