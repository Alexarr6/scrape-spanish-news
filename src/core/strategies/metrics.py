from __future__ import annotations

from typing import Any


def build_strategy_metrics_envelope(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "discovery_strategy_metrics.v1",
        "strategies": rows,
    }
