from __future__ import annotations

import xml.etree.ElementTree as ET

from src.core.adapter import RunConfig
from src.core.http import HttpClient


class RSSDiscoveryStrategy:
    name = "rss"

    def __init__(self, feeds: list[str], http_client: HttpClient | None = None):
        self.feeds = feeds
        self.http = http_client or HttpClient()

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        del target_date  # discovery is source-order based; date filtering happens in extraction
        urls: list[str] = []
        seen: set[str] = set()
        for feed in self.feeds:
            try:
                xml = self.http.get_text(feed)
            except Exception:
                continue

            for link in self._parse_links(xml):
                if not link or link in seen:
                    continue
                seen.add(link)
                urls.append(link)
                if len(urls) >= cfg.max_discovery_urls:
                    return urls
        return urls

    def _parse_links(self, xml_text: str) -> list[str]:
        root = ET.fromstring(xml_text)
        out: list[str] = []
        for item in root.findall(".//item"):
            node = item.find("link")
            if node is None or node.text is None:
                continue
            link = node.text.strip()
            if link:
                out.append(link)
        return out
