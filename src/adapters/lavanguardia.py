from __future__ import annotations

from src.adapters.layered_discovery import DiscoveryLayer, run_layered_discovery
from src.adapters.rss_adapter import GenericRSSAdapter
from src.adapters.url_filters import freshness_priority_key, is_probable_noise_url
from src.core.adapter import RunConfig
from src.core.strategies.metrics import build_strategy_metrics_envelope


class LaVanguardiaAdapter(GenericRSSAdapter):
    source = "lavanguardia"
    feeds = [
        "https://www.lavanguardia.com/rss/home.xml",
        "https://www.lavanguardia.com/rss/politica.xml",
        "https://www.lavanguardia.com/rss/nacional.xml",
    ]
    sitemaps = [
        "https://www.lavanguardia.com/sitemap.xml",
        "https://www.lavanguardia.com/sitemap-noticias.xml",
    ]
    html_fallback_pages = [
        "https://www.lavanguardia.com/politica",
        "https://www.lavanguardia.com/politica/nacional",
        "https://www.lavanguardia.com/vida",
        "https://www.lavanguardia.com/vida/espana",
        "https://www.lavanguardia.com/nacional",
    ]

    def __init__(self, http_client=None):
        super().__init__(http_client=http_client)
        self._strategy_metrics: list[dict] = []

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        urls, metrics = run_layered_discovery(
            cfg=cfg,
            accept=self._accept,
            reject_noise=self._reject_noise,
            order_candidates=lambda candidates: self._order_candidates(candidates, target_date),
            layers=[
                DiscoveryLayer(
                    strategy_name="rss_discovery",
                    load_candidates=lambda: self._discover_links_from_feeds(self.feeds),
                ),
                DiscoveryLayer(
                    strategy_name="sitemap_discovery",
                    load_candidates=lambda: self._discover_links_from_sitemaps(self.sitemaps),
                    min_existing_candidates_to_skip=25,
                ),
                DiscoveryLayer(
                    strategy_name="html_fallback_discovery",
                    load_candidates=lambda: self._discover_links_from_html_pages(
                        self.html_fallback_pages[:5]
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

    def _accept(self, link: str, seen: set[str]) -> bool:
        if not link or link in seen:
            return False
        lo = link.lower()
        if "lavanguardia.com" not in lo:
            return False
        allowed = (
            "/politica/",
            "/nacional/",
            "/espana/",
            "-politica-",
            "-nacional-",
            "-espana-",
        )
        if not any(k in lo for k in allowed):
            return False
        seen.add(link)
        return True

    def _reject_noise(self, link: str) -> bool:
        return is_probable_noise_url(link)

    def _order_candidates(self, candidates: list[str], target_date: str) -> list[str]:
        return sorted(candidates, key=lambda link: freshness_priority_key(link, target_date))
