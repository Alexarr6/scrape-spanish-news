from __future__ import annotations

from src.adapters.layered_discovery import DiscoveryLayer, run_layered_discovery
from src.adapters.rss_adapter import GenericRSSAdapter
from src.adapters.url_filters import is_probable_noise_url
from src.core.adapter import RunConfig
from src.core.strategies.metrics import build_strategy_metrics_envelope


class Minutos20Adapter(GenericRSSAdapter):
    source = "20minutos"
    feeds = [
        "https://www.20minutos.es/rss/",
        "https://www.20minutos.es/rss/nacional/",
        "https://www.20minutos.es/rss/actualidad/",
    ]
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
                    load_candidates=lambda: self._discover_links_from_feeds(self.feeds[:3]),
                ),
                DiscoveryLayer(
                    strategy_name="sitemap_discovery",
                    load_candidates=lambda: self._discover_links_from_sitemaps(self.sitemaps[:3]),
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

    def _reject_noise(self, link: str) -> bool:
        return is_probable_noise_url(link)
