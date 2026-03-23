from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.core.adapter import RunConfig


@dataclass(frozen=True)
class DiscoveryLayer:
    strategy_name: str
    load_candidates: Callable[[], tuple[list[str], int]]
    min_existing_candidates_to_skip: int | None = None


def run_layered_discovery(
    *,
    cfg: RunConfig,
    accept: Callable[[str, set[str]], bool],
    layers: list[DiscoveryLayer],
    reject_noise: Callable[[str], bool] | None = None,
    order_candidates: Callable[[list[str]], list[str]] | None = None,
) -> tuple[list[str], list[dict]]:
    urls: list[str] = []
    seen: set[str] = set()
    metrics: list[dict] = []

    for layer in layers:
        if (
            layer.min_existing_candidates_to_skip is not None
            and len(urls) >= layer.min_existing_candidates_to_skip
        ):
            continue

        candidates, errors = layer.load_candidates()
        if order_candidates is not None:
            candidates = order_candidates(candidates)
        accepted = 0
        rejected_noise = 0
        stop_reason = "completed"
        for link in candidates:
            if reject_noise is not None and reject_noise(link):
                rejected_noise += 1
                continue
            if accept(link, seen):
                urls.append(link)
                accepted += 1
            if len(urls) >= cfg.max_discovery_urls:
                stop_reason = "cap_candidates"
                break

        metrics.append(
            {
                "strategy_name": layer.strategy_name,
                "attempted": len(candidates),
                "accepted": accepted,
                "rejected_noise": rejected_noise,
                "errors": errors,
                "stop_reason": stop_reason,
                "elapsed_ms": 0,
            }
        )
        if stop_reason == "cap_candidates":
            break

    return urls, metrics
