from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from src.adapters.rss_adapter import GenericRSSAdapter
from src.core.adapter import RunConfig
from src.core.strategies.metrics import build_strategy_metrics_envelope


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

    def __init__(self, http_client=None):
        super().__init__(http_client=http_client)
        self._strategy_metrics: list[dict] = []

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        layer_metrics: list[dict] = []

        # Layer 1: RSS
        rss_attempted = 0
        rss_accepted = 0
        for feed in self.feeds:
            try:
                xml = self.http.get_text(feed)
            except Exception:
                continue
            parsed = self._parse_feed(xml)
            rss_attempted += len(parsed)
            for item in parsed:
                link = item.get("link", "")
                if self._accept(link, seen):
                    urls.append(link)
                    rss_accepted += 1
                if len(urls) >= cfg.max_discovery_urls:
                    layer_metrics.append(
                        {
                            "strategy_name": "rss_discovery",
                            "attempted": rss_attempted,
                            "accepted": rss_accepted,
                            "errors": 0,
                            "stop_reason": "cap_candidates",
                            "elapsed_ms": 0,
                        }
                    )
                    self._strategy_metrics = layer_metrics
                    return urls

        layer_metrics.append(
            {
                "strategy_name": "rss_discovery",
                "attempted": rss_attempted,
                "accepted": rss_accepted,
                "errors": 0,
                "stop_reason": "completed",
                "elapsed_ms": 0,
            }
        )

        # Layer 2: sitemap
        sm_attempted = 0
        sm_accepted = 0
        if len(urls) < 25:
            for sm in self.sitemaps:
                try:
                    xml = self.http.get_text(sm)
                except Exception:
                    continue
                parsed = self._parse_sitemap(xml)
                sm_attempted += len(parsed)
                for link in parsed:
                    if self._accept(link, seen):
                        urls.append(link)
                        sm_accepted += 1
                    if len(urls) >= cfg.max_discovery_urls:
                        layer_metrics.append(
                            {
                                "strategy_name": "sitemap_discovery",
                                "attempted": sm_attempted,
                                "accepted": sm_accepted,
                                "errors": 0,
                                "stop_reason": "cap_candidates",
                                "elapsed_ms": 0,
                            }
                        )
                        self._strategy_metrics = layer_metrics
                        return urls

        layer_metrics.append(
            {
                "strategy_name": "sitemap_discovery",
                "attempted": sm_attempted,
                "accepted": sm_accepted,
                "errors": 0,
                "stop_reason": "completed",
                "elapsed_ms": 0,
            }
        )

        # Layer 3: HTML fallback
        html_attempted = 0
        html_accepted = 0
        if len(urls) < 20:
            for page in self.html_fallback_pages:
                try:
                    html = self.http.get_text(page)
                except Exception:
                    continue
                parsed = self._extract_links(html)
                html_attempted += len(parsed)
                for link in parsed:
                    if self._accept(link, seen):
                        urls.append(link)
                        html_accepted += 1
                    if len(urls) >= cfg.max_discovery_urls:
                        layer_metrics.append(
                            {
                                "strategy_name": "html_fallback_discovery",
                                "attempted": html_attempted,
                                "accepted": html_accepted,
                                "errors": 0,
                                "stop_reason": "cap_candidates",
                                "elapsed_ms": 0,
                            }
                        )
                        self._strategy_metrics = layer_metrics
                        return urls

        layer_metrics.append(
            {
                "strategy_name": "html_fallback_discovery",
                "attempted": html_attempted,
                "accepted": html_accepted,
                "errors": 0,
                "stop_reason": "completed",
                "elapsed_ms": 0,
            }
        )

        self._strategy_metrics = layer_metrics
        return urls

    def run(self, target_date: str, cfg: RunConfig):
        articles, metrics = super().run(target_date=target_date, cfg=cfg)
        metrics["strategy_metrics"] = build_strategy_metrics_envelope(self._strategy_metrics)
        return articles, metrics

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
