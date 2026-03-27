from __future__ import annotations

from collections import Counter

from src.analysis.ops.replay.core import ReplayCaseResult


def render_replay_report(results: list[ReplayCaseResult]) -> str:
    lines = []
    pass_count = sum(1 for result in results if result.status == "pass")
    fail_count = len(results) - pass_count
    lines.append(
        f"Editorial replay corpus: {pass_count} passed, {fail_count} failed, {len(results)} total"
    )

    applicability_counts = Counter(
        result.editorial_applicability or result.mode for result in results
    )
    summary_counts = Counter(result.summary_bucket for result in results)
    lines.append("Applicability/mode counts: " + _render_counts(applicability_counts))
    lines.append("Signal bucket counts: " + _render_counts(summary_counts))
    lines.append("")
    for result in results:
        preserved = ", ".join(sorted(result.preserved_signals)) or "-"
        unclear = ", ".join(result.unclear_reasons) or "-"
        dimension_bits = (
            ", ".join(
                f"{name}={status}" for name, status in sorted(result.dimension_status.items())
            )
            or "-"
        )
        lines.append(
            f"[{result.status.upper()}] {result.fixture_id} | family={result.family} | "
            f"mode={result.mode} | applicability={result.editorial_applicability or '-'} | "
            f"bucket={result.summary_bucket}"
        )
        lines.append(f"  unclear_reasons: {unclear}")
        lines.append(f"  dimension_status: {dimension_bits}")
        lines.append(f"  preserved_signals: {preserved}")
        if result.error:
            lines.append(f"  error: {result.error}")
        for mismatch in result.mismatches:
            lines.append(f"  mismatch: {mismatch}")
    return "\n".join(lines)


def _render_counts(counter: Counter[str]) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))
