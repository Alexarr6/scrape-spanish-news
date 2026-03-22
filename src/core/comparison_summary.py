from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .contracts import validate_comparison_summary

REQUIRED_METRIC_KEYS = (
    "discovered",
    "processed",
    "kept",
    "discarded_by_date",
    "stop_reason",
)


@dataclass
class SourceSnapshot:
    source: str
    baseline_count: int
    current_count: int
    metrics: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def _iso_now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _status_for(snapshot: SourceSnapshot) -> str:
    if snapshot.current_count < 0 or snapshot.baseline_count < 0:
        return "invalid"
    if snapshot.warnings:
        return "warning"
    return "ok"



def _derived_warnings_for(snapshot: SourceSnapshot) -> list[str]:
    warnings: list[str] = []
    discovered = _metric_as_int(snapshot.metrics.get("discovered"))
    processed = _metric_as_int(snapshot.metrics.get("processed"))
    kept = _metric_as_int(snapshot.metrics.get("kept"))

    if discovered >= 20 and kept == 0:
        warnings.append("zero_keep_after_discovery")
    elif processed >= 20 and kept / max(processed, 1) < 0.2:
        warnings.append("low_keep_ratio")

    strategy_metrics = snapshot.metrics.get("strategy_metrics")
    if isinstance(strategy_metrics, dict):
        rejected_noise = 0
        for row in strategy_metrics.get("strategies", []):
            if isinstance(row, dict):
                rejected_noise += _metric_as_int(row.get("rejected_noise"))
        if rejected_noise >= 10:
            warnings.append(f"high_noise_rejection:{rejected_noise}")

    return warnings


def _metric_as_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value

def build_comparison_summary(
    *,
    date: str,
    baseline_ref: str,
    current_ref: str,
    snapshots: list[SourceSnapshot],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    global_warnings: list[str] = []

    for snap in snapshots:
        delta_abs = snap.current_count - snap.baseline_count
        delta_pct = 0.0
        if snap.baseline_count > 0:
            delta_pct = round((delta_abs / snap.baseline_count) * 100.0, 2)

        metrics = {k: snap.metrics.get(k) for k in REQUIRED_METRIC_KEYS}
        missing = [k for k, v in metrics.items() if v is None]
        warnings = list(snap.warnings)
        warnings.extend(_derived_warnings_for(snap))
        if missing:
            warnings.append(f"missing_metrics:{','.join(missing)}")

        status = "warning" if warnings else _status_for(snap)
        if warnings:
            global_warnings.extend([f"{snap.source}:{w}" for w in warnings])

        sources.append(
            {
                "source": snap.source,
                "baseline_count": snap.baseline_count,
                "current_count": snap.current_count,
                "delta_abs": delta_abs,
                "delta_pct": delta_pct,
                "status": status,
                "warnings": warnings,
                "metrics": metrics,
            }
        )

    global_status = "warning" if global_warnings else "ok"

    payload = {
        "schema_version": "comparison_summary.v1",
        "generated_at": _iso_now_utc(),
        "date": date,
        "baseline_ref": baseline_ref,
        "current_ref": current_ref,
        "status": global_status,
        "warnings": global_warnings,
        "sources": sources,
    }
    return validate_comparison_summary(payload)
