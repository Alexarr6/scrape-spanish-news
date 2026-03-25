from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.adapters.discovery_profile import CandidateDecision, DiscoveredCandidate
from src.core.adapter import RunConfig

SkipPredicate = Callable[[list[str]], bool]
ClassifyCandidate = Callable[[str | DiscoveredCandidate, set[str]], CandidateDecision]


@dataclass(frozen=True)
class DiscoveryLayer:
    strategy_name: str
    load_candidates: Callable[[], tuple[list[str | DiscoveredCandidate], int]]
    min_existing_candidates_to_skip: int | None = None
    should_skip: SkipPredicate | None = None


def run_layered_discovery(
    *,
    cfg: RunConfig,
    accept: Callable[[str, set[str]], bool] | None = None,
    classify: ClassifyCandidate | None = None,
    layers: list[DiscoveryLayer],
    reject_noise: Callable[[str], bool] | None = None,
    order_candidates: Callable[[list[str | DiscoveredCandidate]], list[str | DiscoveredCandidate]]
    | None = None,
) -> tuple[list[str], list[dict]]:
    urls: list[str] = []
    seen: set[str] = set()
    metrics: list[dict] = []

    for layer in layers:
        if layer.should_skip is not None and layer.should_skip(urls):
            continue
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
        rejected_scope = 0
        rejected_stale = 0
        rejected_locality = 0
        rejected_article_type = 0
        same_local_day_candidates = 0
        stop_reason = "completed"
        for candidate in candidates:
            link = candidate.url if isinstance(candidate, DiscoveredCandidate) else candidate
            if reject_noise is not None and reject_noise(link):
                rejected_noise += 1
                continue
            if classify is not None:
                decision = classify(candidate, seen)
                if decision.accepted:
                    urls.append(link)
                    accepted += 1
                    if decision.same_local_day:
                        same_local_day_candidates += 1
                elif decision.reason == "rejected_noise":
                    rejected_noise += 1
                elif decision.reason == "rejected_stale":
                    rejected_stale += 1
                elif decision.reason == "rejected_locality":
                    rejected_locality += 1
                elif decision.reason == "rejected_article_type":
                    rejected_article_type += 1
                else:
                    rejected_scope += 1
            elif accept is not None and accept(link, seen):
                urls.append(link)
                accepted += 1
            else:
                rejected_scope += 1
            if len(urls) >= cfg.max_discovery_urls:
                stop_reason = "cap_candidates"
                break

        metrics.append(
            {
                "strategy_name": layer.strategy_name,
                "attempted": len(candidates),
                "accepted": accepted,
                "rejected_noise": rejected_noise,
                "rejected_scope": rejected_scope,
                "rejected_stale": rejected_stale,
                "rejected_locality": rejected_locality,
                "rejected_article_type": rejected_article_type,
                "same_local_day_candidates": same_local_day_candidates,
                "errors": errors,
                "stop_reason": stop_reason,
                "elapsed_ms": 0,
            }
        )
        if stop_reason == "cap_candidates":
            break

    return urls, metrics
