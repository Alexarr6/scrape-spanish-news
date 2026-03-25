from __future__ import annotations

from src.core.comparison_summary import SourceSnapshot, build_comparison_summary


def test_build_comparison_summary_flags_low_keep_ratio_and_noise_rejection() -> None:
    summary = build_comparison_summary(
        date="2026-03-13",
        baseline_ref="baseline",
        current_ref="current",
        snapshots=[
            SourceSnapshot(
                source="abc",
                baseline_count=10,
                current_count=2,
                metrics={
                    "discovered": 40,
                    "processed": 25,
                    "kept": 2,
                    "discarded_by_date": 3,
                    "stop_reason": "completed",
                    "strategy_metrics": {
                        "schema_version": "discovery_strategy_metrics.v1",
                        "strategies": [
                            {"strategy_name": "rss", "rejected_noise": 12},
                        ],
                    },
                },
            )
        ],
    )

    row = summary["sources"][0]
    assert row["status"] == "warning"
    assert "low_keep_ratio" in row["warnings"]
    assert "high_noise_rejection:12" in row["warnings"]
