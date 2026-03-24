from __future__ import annotations

import re
from urllib.parse import urlparse

from src.adapters.layered_discovery import DiscoveryLayer, run_layered_discovery
from src.adapters.rss_adapter import GenericRSSAdapter
from src.adapters.url_filters import is_probable_noise_url
from src.core.adapter import RunConfig
from src.core.strategies.metrics import build_strategy_metrics_envelope


class ElDiarioAdapter(GenericRSSAdapter):
    source = "eldiario"

    feeds = [
        "https://www.eldiario.es/rss/",
        "https://www.eldiario.es/rss/politica/",
        "https://www.eldiario.es/rss/sociedad/",
    ]
    sitemaps = [
        "https://www.eldiario.es/sitemap_index.xml",
        "https://www.eldiario.es/sitemap_google_news.xml",
        "https://www.eldiario.es/sitemap.xml",
    ]
    html_fallback_pages = [
        "https://www.eldiario.es/politica/",
        "https://www.eldiario.es/sociedad/",
        "https://www.eldiario.es/",
    ]

    def __init__(self, http_client=None):
        super().__init__(http_client=http_client)
        self._strategy_metrics: list[dict] = []

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        urls, metrics = run_layered_discovery(
            cfg=cfg,
            accept=self._accept,
            reject_noise=self._reject_noise,
            layers=[
                DiscoveryLayer(
                    strategy_name="rss_discovery",
                    load_candidates=lambda: self._discover_links_from_feeds(self.feeds[:3]),
                ),
                DiscoveryLayer(
                    strategy_name="sitemap_discovery",
                    load_candidates=lambda: self._discover_links_from_sitemaps(
                        (self.sitemaps + self._collect_sitemaps_from_robots())[:6]
                    ),
                    min_existing_candidates_to_skip=25,
                ),
                DiscoveryLayer(
                    strategy_name="html_fallback_discovery",
                    load_candidates=lambda: self._discover_links_from_html_pages(
                        self.html_fallback_pages[:3]
                    ),
                    min_existing_candidates_to_skip=20,
                ),
            ],
        )
        self._strategy_metrics = metrics
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
        out: list[str] = []
        seen: set[str] = set()
        for sitemap in found:
            sitemap = sitemap.strip()
            if sitemap and sitemap not in seen:
                seen.add(sitemap)
                out.append(sitemap)
        return out

    def _accept(self, link: str, seen: set[str]) -> bool:
        if not link or link in seen:
            return False
        lo = link.lower()
        if "eldiario.es" not in lo:
            return False
        allowed = ("/politica/", "/sociedad/", "/nacional/", "/espana/")
        if not any(k in lo for k in allowed):
            return False
        seen.add(link)
        return True

    def _reject_noise(self, link: str) -> bool:
        return is_probable_noise_url(link)

    def _has_enough_usable_candidates(
        self, urls: list[str], *, target_date: str, minimum: int
    ) -> bool:
        usable = sum(
            1
            for link in urls
            if self._is_probably_usable_candidate(link, target_date=target_date)
        )
        return usable >= minimum

    def _is_probably_usable_candidate(self, link: str, *, target_date: str) -> bool:
        if self._reject_noise(link):
            return False
        parsed = urlparse(link)
        path = (parsed.path or "").lower()
        if not path or path in {"/", ""}:
            return False
        if target_date:
            date_variants = [target_date.replace("-", "/"), target_date.replace("-", "")]
            if any(variant and variant in path for variant in date_variants):
                return True
            if re.search(r"/20\d{2}/\d{2}/\d{2}/", path) or re.search(r"/20\d{6}/", path):
                return False
        return any(
            segment in path
            for segment in ("/politica/", "/sociedad/", "/nacional/", "/espana/")
        )
