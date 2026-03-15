from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.adapter import RunConfig


class DiscoveryStrategy(Protocol):
    name: str

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        ...


@dataclass
class StrategyMetrics:
    strategy_name: str
    attempted: int = 0
    accepted: int = 0
    rejected_by_date: int = 0
    rejected_noise: int = 0
    errors: int = 0
    elapsed_ms: int = 0
    stop_reason: str = "completed"
