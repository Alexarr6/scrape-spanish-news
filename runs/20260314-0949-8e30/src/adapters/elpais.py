from __future__ import annotations

from src.core.adapter import RunConfig
from src.core.strategies.orchestrator import DiscoveryOrchestrator
from src.core.strategies.rss_discovery import RSSDiscoveryStrategy

from .rss_adapter import GenericRSSAdapter


class ElPaisAdapter(GenericRSSAdapter):
    source = "elpais"
    feeds = [
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada",
    ]

    def __init__(self, http_client=None):
        super().__init__(http_client=http_client)
        self._strategy_metrics: list[dict] = []

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        orchestrator = DiscoveryOrchestrator(
            [
                RSSDiscoveryStrategy(feeds=self.feeds, http_client=self.http),
            ]
        )
        urls, metrics = orchestrator.run(target_date=target_date, cfg=cfg)
        self._strategy_metrics = metrics
        return urls

    def run(self, target_date: str, cfg: RunConfig):
        articles, metrics = super().run(target_date=target_date, cfg=cfg)
        metrics["strategy_metrics"] = self._strategy_metrics
        return articles, metrics
