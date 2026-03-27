from __future__ import annotations

from collections import Counter, defaultdict
from math import isfinite

from src.analysis.readside.editorial_summary_parts.json_payloads import (
    parse_json_list,
    parse_json_scalar_list,
)
from src.analysis.readside.editorial_summary_parts.review_flags import build_review_flags
from src.analysis.store.models import ArticleEditorialAnalysisORM


def build_cluster_comparative_metrics(
    members, editorial_rows: dict[int, ArticleEditorialAnalysisORM]
) -> dict:
    minimum_articles_per_source = 2
    source_articles: dict[str, list[dict]] = defaultdict(list)

    for member in members:
        analysis = editorial_rows.get(member.article_id)
        if analysis is None:
            continue
        review_flags = build_review_flags(
            analysis_status=analysis.analysis_status,
            bias_label=analysis.bias_label,
            bias_confidence=float(analysis.bias_confidence),
            evidence_spans=parse_json_list(analysis.evidence_spans_json),
            unclear_reasons=parse_json_scalar_list(analysis.unclear_reasons_json),
            editorial_applicability=analysis.editorial_applicability,
        )
        source_articles[member.source].append(
            {
                "article_id": member.article_id,
                "analysis": analysis,
                "review_flags": review_flags,
                "framing_devices": parse_json_scalar_list(analysis.framing_devices_json),
            }
        )

    included_sources = []
    source_metrics = []
    source_payloads: dict[str, dict] = {}

    for source in sorted(source_articles):
        rows = source_articles[source]
        usable_rows = [
            row for row in rows if is_editorial_row_usable_for_dimension(row["analysis"])
        ]
        full_count = sum(
            1 for row in usable_rows if row["analysis"].editorial_applicability == "full"
        )
        limited_count = sum(
            1 for row in usable_rows if row["analysis"].editorial_applicability == "limited"
        )
        low_confidence_count = sum(
            1 for row in usable_rows if row["review_flags"]["low_confidence"]
        )

        if len(usable_rows) < minimum_articles_per_source:
            eligibility = "insufficient_sample"
            comparison_note = (
                f"Only {len(usable_rows)} usable analyzed article"
                f"{'s' if len(usable_rows) != 1 else ''} in this cluster."
            )
        elif full_count == 0 or limited_count >= full_count:
            eligibility = "limited"
            comparison_note = (
                "Comparison is limited because usable coverage is mostly partial or"
                " domain-constrained in this cluster."
            )
        else:
            eligibility = "eligible"
            comparison_note = "Enough usable cluster-scoped coverage for cautious comparison."

        included_sources.append(
            {
                "source": source,
                "usable_article_count": len(usable_rows),
                "full_applicability_count": full_count,
                "limited_applicability_count": limited_count,
                "low_confidence_count": low_confidence_count,
                "comparison_eligibility": eligibility,
                "comparison_note": comparison_note,
            }
        )

        metric_payload = compute_source_dimension_index(source, usable_rows, eligibility)
        source_metrics.append(metric_payload)
        source_payloads[source] = {
            "source": source,
            "eligibility": eligibility,
            "metric_payload": metric_payload,
            "usable_rows": usable_rows,
        }

    divergence_signals = build_divergence_signals(source_payloads)
    eligible_source_count = sum(
        1 for item in included_sources if item["comparison_eligibility"] in {"eligible", "limited"}
    )

    if not included_sources:
        comparison_note = "No completed editorial rows are available for cluster comparison yet."
    elif eligible_source_count < 2:
        comparison_note = (
            "Comparative signals are suppressed because fewer than two sources have enough"
            " usable cluster-scoped coverage."
        )
    elif not divergence_signals:
        comparison_note = (
            "Compared sources are present, but no dimension cleared the support threshold for"
            " a sober divergence claim in this cluster."
        )
    else:
        comparison_note = (
            "Comparative signals are cluster-scoped and sample-aware across "
            f"{eligible_source_count} sources; weaker or mixed dimensions stay hidden."
        )

    return {
        "eligible_source_count": eligible_source_count,
        "minimum_articles_per_source": minimum_articles_per_source,
        "included_sources": included_sources,
        "source_metrics": source_metrics,
        "divergence_signals": divergence_signals,
        "comparison_note": comparison_note,
    }


def compute_source_dimension_index(source: str, usable_rows: list[dict], eligibility: str) -> dict:
    metric_notes: list[str] = []
    usable_article_count = len(usable_rows)
    low_confidence_count = sum(1 for row in usable_rows if row["review_flags"]["low_confidence"])
    limited_count = sum(
        1 for row in usable_rows if row["analysis"].editorial_applicability == "limited"
    )

    if usable_article_count < 2:
        metric_notes.append("Too few usable articles for comparison-grade source metrics.")
    if limited_count:
        metric_notes.append(f"{limited_count} usable article(s) are limited-applicability reads.")
    if low_confidence_count:
        metric_notes.append(f"{low_confidence_count} usable article(s) have low bias confidence.")

    opinionatedness_index, opinionated_support = average_dimension_index(
        usable_rows,
        value_getter=lambda row: map_opinionatedness(row["analysis"].opinionatedness),
        status_getter=lambda row: row["analysis"].opinionatedness_status,
        min_support=2,
    )
    if opinionatedness_index is None:
        metric_notes.append(
            "Opinionatedness stayed mixed or under-supported, so the index is hidden."
        )

    emotional_tone_index, tone_support = average_dimension_index(
        usable_rows,
        value_getter=lambda row: map_tone(row["analysis"].tone_emotional),
        status_getter=lambda row: row["analysis"].tone_emotional_status,
        min_support=2,
    )
    if emotional_tone_index is None:
        metric_notes.append("Tone stayed mixed or under-supported, so the index is hidden.")

    bias_direction_index, bias_support = average_dimension_index(
        usable_rows,
        value_getter=lambda row: map_bias_direction(row["analysis"].bias_label),
        status_getter=lambda row: row["analysis"].bias_status,
        min_support=2,
    )
    if bias_direction_index is None:
        metric_notes.append("Bias direction stayed weak, mixed, or too thin for a cluster claim.")

    framing_values = []
    framing_support_rows = []
    for row in usable_rows:
        analysis = row["analysis"]
        if analysis.framing_status != "resolved":
            continue
        framing_devices = row["framing_devices"]
        if not framing_devices:
            continue
        framing_support_rows.append(row)
        counts = Counter(framing_devices)
        framing_values.append(max(counts.values()) / max(len(framing_devices), 1))
    framing_concentration_index = None
    if len(framing_values) >= 2:
        framing_concentration_index = round(sum(framing_values) / len(framing_values), 3)
    else:
        metric_notes.append("Framing concentration is hidden because framing support is too thin.")

    confidence_band = "high"
    if usable_article_count < 2:
        confidence_band = "insufficient"
    elif eligibility == "limited" or limited_count:
        confidence_band = "low"
    elif low_confidence_count:
        confidence_band = "moderate"
    if usable_article_count >= 3 and eligibility == "eligible" and low_confidence_count == 0:
        confidence_band = "high"

    return {
        "source": source,
        "usable_article_count": usable_article_count,
        "opinionatedness_index": opinionatedness_index,
        "emotional_tone_index": emotional_tone_index,
        "bias_direction_index": bias_direction_index,
        "framing_concentration_index": framing_concentration_index,
        "confidence_band": confidence_band,
        "metric_notes": list(dict.fromkeys(metric_notes)),
        "_dimension_support": {
            "opinionatedness": opinionated_support,
            "tone": tone_support,
            "bias": bias_support,
            "framing": len(framing_support_rows),
        },
    }


def build_divergence_signals(source_payloads: dict[str, dict]) -> list[dict]:
    eligible_sources = [
        payload
        for payload in source_payloads.values()
        if payload["eligibility"] in {"eligible", "limited"}
    ]
    if len(eligible_sources) < 2:
        return []

    dimensions = {
        "opinionatedness": (
            "opinionatedness_index",
            0.34,
            0.66,
            "More opinionated mix in this cluster",
        ),
        "tone": (
            "emotional_tone_index",
            0.34,
            0.66,
            "More emotional tone mix in this cluster",
        ),
        "bias": (
            "bias_direction_index",
            0.75,
            1.25,
            "Different bias-direction mix in this cluster",
        ),
        "framing": (
            "framing_concentration_index",
            0.2,
            0.35,
            "More concentrated framing pattern in this cluster",
        ),
    }
    signals = []
    for dimension, (field, moderate_threshold, strong_threshold, label) in dimensions.items():
        best_signal = None
        for leading in eligible_sources:
            for trailing in eligible_sources:
                if leading["source"] == trailing["source"]:
                    continue
                leading_value = leading["metric_payload"].get(field)
                trailing_value = trailing["metric_payload"].get(field)
                if leading_value is None or trailing_value is None:
                    continue
                delta = leading_value - trailing_value
                if not isfinite(delta) or delta < moderate_threshold:
                    continue
                leading_support = leading["metric_payload"]["_dimension_support"].get(
                    dimension, 0
                )
                trailing_support = trailing["metric_payload"]["_dimension_support"].get(
                    dimension, 0
                )
                if leading_support < 2 or trailing_support < 2:
                    continue
                strength = "strong" if delta >= strong_threshold else "moderate"
                candidate = {
                    "dimension": dimension,
                    "label": label,
                    "leading_source": leading["source"],
                    "trailing_source": trailing["source"],
                    "delta": round(delta, 3),
                    "strength": strength,
                    "support": {
                        "leading_usable_articles": leading_support,
                        "trailing_usable_articles": trailing_support,
                        "compared_sources": sorted([leading["source"], trailing["source"]]),
                    },
                    "note": (
                        f"This difference is limited to the current cluster and based on"
                        f" {leading_support} vs {trailing_support} usable article(s)."
                    ),
                    "example_article_ids": example_article_ids_for_dimension(
                        leading["usable_rows"], dimension
                    ),
                }
                if best_signal is None or candidate["delta"] > best_signal["delta"]:
                    best_signal = candidate
        if best_signal is not None:
            signals.append(best_signal)
    return signals


def example_article_ids_for_dimension(usable_rows: list[dict], dimension: str) -> list[int]:
    article_ids = []
    for row in usable_rows:
        analysis = row["analysis"]
        if (
            dimension == "framing"
            and analysis.framing_status == "resolved"
            and row["framing_devices"]
        ):
            article_ids.append(row["article_id"])
        elif dimension == "bias" and analysis.bias_status == "resolved":
            article_ids.append(row["article_id"])
        elif dimension == "tone" and analysis.tone_emotional_status == "resolved":
            article_ids.append(row["article_id"])
        elif dimension == "opinionatedness" and analysis.opinionatedness_status == "resolved":
            article_ids.append(row["article_id"])
        if len(article_ids) >= 3:
            break
    return article_ids


def average_dimension_index(
    usable_rows: list[dict], *, value_getter, status_getter, min_support: int = 2
) -> tuple[float | None, int]:
    values = []
    for row in usable_rows:
        status = status_getter(row)
        if status != "resolved":
            continue
        value = value_getter(row)
        if value is None:
            continue
        values.append(value)
    if len(values) < min_support:
        return None, len(values)
    return round(sum(values) / len(values), 3), len(values)


def is_editorial_row_usable_for_dimension(analysis: ArticleEditorialAnalysisORM) -> bool:
    return (
        analysis.analysis_status == "completed"
        and analysis.editorial_applicability != "out_of_domain"
    )


def map_opinionatedness(value: str) -> float | None:
    return {"low": 0.0, "mixed": 0.5, "high": 1.0}.get(value)


def map_tone(value: str) -> float | None:
    return {
        "measured": 0.0,
        "somewhat_emotional": 0.5,
        "critical": 1.0,
        "emotional": 1.0,
    }.get(value)


def map_bias_direction(value: str) -> float | None:
    return {
        "left": -1.0,
        "center_left": -0.5,
        "unclear": 0.0,
        "center": 0.0,
        "center_right": 0.5,
        "right": 1.0,
    }.get(value)
