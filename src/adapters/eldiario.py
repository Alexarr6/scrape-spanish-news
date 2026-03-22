from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from src.adapters.rss_adapter import GenericRSSAdapter
from src.core.adapter import RunConfig
from src.core.strategies.metrics import build_strategy_metrics_envelope


class ElDiarioAdapter(GenericRSSAdapter):
    source = "eldiario"

    # Capa primaria: RSS editoriales con mejor señal para España/política.
    feeds = [
        "https://www.eldiario.es/rss/",
        "https://www.eldiario.es/rss/politica/",
        "https://www.eldiario.es/rss/sociedad/",
    ]

    # Capa intermedia: candidatos estáticos + descubrimiento dinámico desde robots.txt.
    sitemaps = [
        "https://www.eldiario.es/sitemap_index.xml",
        "https://www.eldiario.es/sitemap_google_news.xml",
        "https://www.eldiario.es/sitemap.xml",
    ]

    # Último recurso, listados HTML.
    html_fallback_pages = [
        "https://www.eldiario.es/politica/",
        "https://www.eldiario.es/sociedad/",
        "https://www.eldiario.es/",
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
        for feed in self.feeds[:3]:
            try:
                xml = self.http.get_text(feed)
            except Exception:
                continue
            parsed = self._parse_feed(xml)
            rss_attempted += len(parsed)
            for item in parsed:
                if self._accept(item.get("link", ""), seen):
                    urls.append(item["link"])
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

        # Layer 2: sitemaps (incluye discovery dinámico desde robots)
        sm_attempted = 0
        sm_accepted = 0
        if len(urls) < 25:
            sitemap_candidates = self._collect_sitemaps_from_robots()
            for sm in (self.sitemaps + sitemap_candidates)[:6]:
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
            for page in self.html_fallback_pages[:3]:
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

    def _collect_sitemaps_from_robots(self) -> list[str]:
        try:
            robots = self.http.get_text("https://www.eldiario.es/robots.txt")
        except Exception:
            return []
        found = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots)
        # mantener orden y dedupe
        out: list[str] = []
        seen: set[str] = set()
        for sm in found:
            sm = sm.strip()
            if sm and sm not in seen:
                seen.add(sm)
                out.append(sm)
        return out

    def _parse_sitemap(self, xml_text: str) -> list[str]:
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return []

        links: list[str] = []
        for loc in root.findall(".//{*}loc"):
            if loc.text:
                links.append(loc.text.strip())
        return links

    def _extract_links(self, html: str) -> list[str]:
        return re.findall(r'href=["\'](https://www\.eldiario\.es[^"\']+)["\']', html)

    def _accept(self, link: str, seen: set[str]) -> bool:
        if not link or link in seen:
            return False

        lo = link.lower()
        if "www.eldiario.es" not in lo:
            return False
        if any(x in lo for x in ("/autor/", "/rss/", "/opiniones/", "/ultima-hora/")):
            return False

        allowed = (
            "/politica/",
            "/sociedad/",
            "/nacional/",
            "/espana/",
            "-espana-",
            "-politica-",
        )
        if not any(k in lo for k in allowed):
            return False

        seen.add(link)
        return True
