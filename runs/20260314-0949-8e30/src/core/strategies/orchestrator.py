from __future__ import annotations

import time
from dataclasses import asdict

from src.core.adapter import RunConfig

from .base import StrategyMetrics


class DiscoveryOrchestrator:
    def __init__(self, strategies: list):
        self.strategies = strategies

    def run(self, target_date: str, cfg: RunConfig) -> tuple[list[str], list[dict]]:
        urls: list[str] = []
        seen: set[str] = set()
        per_strategy: list[dict] = []

        for strategy in self.strategies:
            started = time.time()
            metrics = StrategyMetrics(strategy_name=getattr(strategy, "name", strategy.__class__.__name__))
            try:
                discovered = strategy.discover(target_date=target_date, cfg=cfg)
                metrics.attempted = len(discovered)
                for link in discovered:
                    if link in seen:
                        continue
                    seen.add(link)
                    urls.append(link)
                    metrics.accepted += 1
                    if len(urls) >= cfg.max_discovery_urls:
                        metrics.stop_reason = "cap_candidates"
                        break
            except Exception:
                metrics.errors += 1
                metrics.stop_reason = "strategy_error"

            metrics.elapsed_ms = int((time.time() - started) * 1000)
            per_strategy.append(asdict(metrics))

            if len(urls) >= cfg.max_discovery_urls:
                break

        return urls, per_strategy
