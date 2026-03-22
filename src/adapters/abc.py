from __future__ import annotations

from src.adapters.layered_discovery import DiscoveryLayer, run_layered_discovery
from src.adapters.rss_adapter import GenericRSSAdapter
from src.adapters.url_filters import is_probable_noise_url
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
        del target_date
        urls, metrics = run_layered_discovery(
            cfg=cfg,
            accept=self._accept,
            reject_noise=self._reject_noise,
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
                        self.html_fallback_pages
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
        allowed = ("/espana/", "/politica/", "/nacional/")
        if not any(k in lo for k in allowed):
            return False
        seen.add(link)
        return True

    def _reject_noise(self, link: str) -> bool:
        return is_probable_noise_url(link)
