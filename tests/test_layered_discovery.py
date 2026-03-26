from __future__ import annotations

from src.adapters.layered_discovery import DiscoveryLayer, run_layered_discovery
from src.core.adapter import RunConfig


def test_layered_discovery_tracks_rejected_noise_and_cap() -> None:
    urls, metrics = run_layered_discovery(
        cfg=RunConfig(max_discovery_urls=2),
        accept=lambda link, seen: False if link in seen else not seen.add(link),
        reject_noise=lambda link: "weather" in link,
        layers=[
            DiscoveryLayer(
                strategy_name="rss_discovery",
                load_candidates=lambda: (
                    [
                        "https://example.com/politica/a",
                        "https://example.com/weather/b",
                        "https://example.com/politica/c",
                    ],
                    0,
                ),
            )
        ],
    )

    assert urls == ["https://example.com/politica/a", "https://example.com/politica/c"]
    assert metrics == [
        {
            "strategy_name": "rss_discovery",
            "attempted": 3,
            "accepted": 2,
            "rejected_noise": 1,
            "rejected_scope": 0,
            "rejected_stale": 0,
            "rejected_locality": 0,
            "rejected_article_type": 0,
            "same_local_day_candidates": 0,
            "errors": 0,
            "stop_reason": "cap_candidates",
            "elapsed_ms": 0,
        }
    ]


def test_layered_discovery_can_order_candidates_before_acceptance() -> None:
    urls, _ = run_layered_discovery(
        cfg=RunConfig(max_discovery_urls=3),
        accept=lambda link, seen: False if link in seen else not seen.add(link),
        order_candidates=lambda candidates: sorted(candidates, reverse=True),
        layers=[
            DiscoveryLayer(
                strategy_name="rss_discovery",
                load_candidates=lambda: (
                    [
                        "https://example.com/politica/a",
                        "https://example.com/politica/c",
                        "https://example.com/politica/b",
                    ],
                    0,
                ),
            )
        ],
    )

    assert urls == [
        "https://example.com/politica/c",
        "https://example.com/politica/b",
        "https://example.com/politica/a",
    ]
