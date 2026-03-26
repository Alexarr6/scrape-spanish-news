from __future__ import annotations

import json
from collections import Counter, defaultdict
from math import isfinite

from src.analysis.orm_models import ArticleEditorialAnalysisORM


def shape_product_editorial_summary(
    article_id: int, analysis: ArticleEditorialAnalysisORM | None
) -> dict:
    if analysis is None:
        return {
            "article_id": article_id,
            "analysis_status": "pending",
            "editorial_applicability": "full",
            "editorial_applicability_reason": "general_editorial_content",
            "article_type": "unclear",
            "article_type_confidence": 0.0,
            "bias_label": "unclear",
            "bias_score": 0.0,
            "bias_confidence": 0.0,
            "tone_emotional": "unclear",
            "tone_target": "unclear",
            "opinionatedness": "unclear",
            "sensationalism": "unclear",
            "rhetorical_certainty": "unclear",
            "framing_devices": [],
            "evidence_spans": [],
            "rationale": "Editorial analysis pending.",
            "unclear_reasons": [],
            "review_flags": build_review_flags(
                analysis_status="pending",
                bias_label="unclear",
                bias_confidence=0.0,
                evidence_spans=[],
                unclear_reasons=[],
                editorial_applicability="full",
            ),
            "diagnostics_summary": None,
        }
    evidence_spans = parse_json_list(analysis.evidence_spans_json)
    unclear_reasons = parse_json_scalar_list(analysis.unclear_reasons_json)
    diagnostics = parse_json_object(analysis.diagnostics_json)
    return {
        "article_id": article_id,
        "analysis_status": analysis.analysis_status,
        "editorial_applicability": analysis.editorial_applicability,
        "editorial_applicability_reason": analysis.editorial_applicability_reason,
        "article_type": analysis.article_type,
        "article_type_confidence": float(analysis.article_type_confidence),
        "bias_label": analysis.bias_label,
        "bias_score": float(analysis.bias_score),
        "bias_confidence": float(analysis.bias_confidence),
        "tone_emotional": analysis.tone_emotional,
        "tone_target": analysis.tone_target,
        "opinionatedness": analysis.opinionatedness,
        "sensationalism": analysis.sensationalism,
        "rhetorical_certainty": analysis.rhetorical_certainty,
        "framing_devices": parse_json_scalar_list(analysis.framing_devices_json),
        "evidence_spans": [
            {
                "type": str(item.get("type") or item.get("kind") or "quote"),
                "text": str(item.get("text") or item.get("span") or ""),
                "note": str(item.get("note") or item.get("context") or ""),
            }
            for item in evidence_spans[:3]
            if isinstance(item, dict) and (item.get("text") or item.get("span"))
        ],
        "rationale": analysis.rationale or "",
        "unclear_reasons": unclear_reasons,
        "review_flags": build_review_flags(
            analysis_status=analysis.analysis_status,
            bias_label=analysis.bias_label,
            bias_confidence=float(analysis.bias_confidence),
            evidence_spans=evidence_spans,
            unclear_reasons=unclear_reasons,
            editorial_applicability=analysis.editorial_applicability,
        ),
        "diagnostics_summary": {
            "dimension_status": {
                key: value
                for key, value in {
                    "article_type": analysis.article_type_status,
                    "bias": analysis.bias_status,
                    "tone_emotional": analysis.tone_emotional_status,
                    "tone_target": analysis.tone_target_status,
                    "opinionatedness": analysis.opinionatedness_status,
                    "sensationalism": analysis.sensationalism_status,
                    "rhetorical_certainty": analysis.rhetorical_certainty_status,
                    "framing": analysis.framing_status,
                }.items()
                if value
            }
        }
        if diagnostics or any(
            [
                analysis.article_type_status,
                analysis.bias_status,
                analysis.tone_emotional_status,
                analysis.tone_target_status,
                analysis.opinionatedness_status,
                analysis.sensationalism_status,
                analysis.rhetorical_certainty_status,
                analysis.framing_status,
            ]
        )
        else None,
    }


def shape_member_editorial_preview(analysis: ArticleEditorialAnalysisORM | None) -> dict:
    summary = shape_product_editorial_summary(getattr(analysis, "article_id", 0), analysis)
    return {
        "analysis_status": summary["analysis_status"],
        "article_type": summary["article_type"],
        "article_type_confidence": summary["article_type_confidence"],
        "bias_label": summary["bias_label"],
        "bias_confidence": summary["bias_confidence"],
        "editorial_applicability": summary["editorial_applicability"],
        "review_flags": {
            "low_confidence": summary["review_flags"]["low_confidence"],
            "needs_review": summary["review_flags"]["needs_review"],
            "unclear_bias": summary["review_flags"]["unclear_bias"],
            "out_of_domain": summary["review_flags"]["out_of_domain"],
            "pending_analysis": summary["review_flags"]["pending_analysis"],
        },
    }


def build_cluster_editorial_summary(
    members, editorial_rows: dict[int, ArticleEditorialAnalysisORM]
) -> dict:
    total_members = len(members)
    analyzed_count = 0
    pending_count = 0
    failed_count = 0
    applicability_breakdown: Counter[str] = Counter()
    article_type_breakdown: Counter[str] = Counter()
    source_buckets: dict[str, dict] = {}
    framing_examples: dict[str, list[int]] = defaultdict(list)
    framing_sources: dict[str, set[str]] = defaultdict(set)
    bias_labels_present: set[str] = set()

    for member in members:
        source_bucket = source_buckets.setdefault(
            member.source,
            {
                "source": member.source,
                "article_count": 0,
                "analyzed_article_count": 0,
                "applicability_breakdown": Counter(),
                "article_type_breakdown": Counter(),
                "bias_label_breakdown": Counter(),
                "opinionatedness_breakdown": Counter(),
                "tone_emotional_breakdown": Counter(),
                "top_framing_devices": Counter(),
                "framing_examples": defaultdict(list),
                "review_flag_counts": {
                    "low_confidence": 0,
                    "needs_review": 0,
                    "out_of_domain": 0,
                    "limited": 0,
                },
            },
        )
        source_bucket["article_count"] += 1
        analysis = editorial_rows.get(member.article_id)
        if analysis is None:
            pending_count += 1
            continue
        summary = shape_product_editorial_summary(member.article_id, analysis)
        if analysis.analysis_status == "completed":
            analyzed_count += 1
            source_bucket["analyzed_article_count"] += 1
        elif analysis.analysis_status == "pending":
            pending_count += 1
        elif analysis.analysis_status == "failed":
            failed_count += 1

        applicability = summary["editorial_applicability"]
        applicability_breakdown[applicability] += 1
        source_bucket["applicability_breakdown"][applicability] += 1
        article_type_breakdown[summary["article_type"]] += 1
        source_bucket["article_type_breakdown"][summary["article_type"]] += 1
        source_bucket["bias_label_breakdown"][summary["bias_label"]] += 1
        source_bucket["opinionatedness_breakdown"][summary["opinionatedness"]] += 1
        source_bucket["tone_emotional_breakdown"][summary["tone_emotional"]] += 1
        if summary["bias_label"] not in {"", "unclear"}:
            bias_labels_present.add(summary["bias_label"])
        for device in summary["framing_devices"]:
            source_bucket["top_framing_devices"][device] += 1
            if len(source_bucket["framing_examples"][device]) < 3:
                source_bucket["framing_examples"][device].append(member.article_id)
            if len(framing_examples[device]) < 4:
                framing_examples[device].append(member.article_id)
            framing_sources[device].add(member.source)
        flags = summary["review_flags"]
        if flags["low_confidence"]:
            source_bucket["review_flag_counts"]["low_confidence"] += 1
        if flags["needs_review"]:
            source_bucket["review_flag_counts"]["needs_review"] += 1
        if flags["out_of_domain"]:
            source_bucket["review_flag_counts"]["out_of_domain"] += 1
        if applicability == "limited":
            source_bucket["review_flag_counts"]["limited"] += 1

    source_summaries = []
    for source in sorted(source_buckets):
        bucket = source_buckets[source]
        top_framing_devices = []
        for device, count in bucket["top_framing_devices"].most_common(3):
            if count < 1:
                continue
            top_framing_devices.append(
                {
                    "framing_device": device,
                    "count": count,
                    "example_article_ids": bucket["framing_examples"][device][:3],
                }
            )
        source_summaries.append(
            {
                "source": source,
                "article_count": bucket["article_count"],
                "analyzed_article_count": bucket["analyzed_article_count"],
                "applicability_breakdown": dict(bucket["applicability_breakdown"]),
                "article_type_breakdown": dict(bucket["article_type_breakdown"]),
                "bias_label_breakdown": dict(bucket["bias_label_breakdown"]),
                "opinionatedness_breakdown": dict(bucket["opinionatedness_breakdown"]),
                "tone_emotional_breakdown": dict(bucket["tone_emotional_breakdown"]),
                "top_framing_devices": top_framing_devices,
                "review_flag_counts": bucket["review_flag_counts"],
            }
        )

    cluster_signals = []
    for device, article_ids in sorted(
        framing_examples.items(), key=lambda item: (-len(item[1]), item[0])
    )[:3]:
        support = len(article_ids)
        if support < 2:
            continue
        strength = "strong" if support >= 3 else "moderate"
        cluster_signals.append(
            {
                "label": f"Framing device: {device}",
                "strength": strength,
                "supporting_sources": sorted(framing_sources[device]),
                "example_article_ids": article_ids[:4],
                "note": (
                    f"Seen in {support} analyzed articles across "
                    f"{len(framing_sources[device])} sources."
                ),
            }
        )
    if not cluster_signals and analyzed_count:
        cluster_signals.append(
            {
                "label": "Framing signal is mixed",
                "strength": "weak",
                "supporting_sources": sorted(source_buckets.keys()),
                "example_article_ids": [],
                "note": (
                    "No framing device cleared the support threshold "
                    "for a confident cluster-level claim."
                ),
            }
        )
    if len(bias_labels_present) > 1:
        cluster_signals.append(
            {
                "label": "Bias labels are contested across the cluster",
                "strength": "moderate" if analyzed_count >= 3 else "weak",
                "supporting_sources": sorted(source_buckets.keys()),
                "example_article_ids": [],
                "note": (
                    "Different analyzed articles resolve to different bias "
                    "labels, so treat this story as mixed rather than "
                    "reducible to one label."
                ),
            }
        )

    confidence_note = (
        f"Interpretation is based on {analyzed_count} analyzed articles out of {total_members}. "
        f"Pending: {pending_count}. Failed: {failed_count}."
    )
    if analyzed_count == 0:
        confidence_note = (
            "Editorial comparison is not yet reliable for this cluster because "
            "no member articles have completed analysis."
        )
    elif (
        pending_count
        or failed_count
        or applicability_breakdown.get("limited")
        or applicability_breakdown.get("out_of_domain")
    ):
        confidence_note += (
            " Signal is partial: pending, failed, limited, or out-of-domain "
            "items remain visible in the summary."
        )

    return {
        "analyzed_article_count": analyzed_count,
        "pending_article_count": pending_count,
        "failed_article_count": failed_count,
        "applicability_breakdown": dict(applicability_breakdown),
        "article_type_breakdown": dict(article_type_breakdown),
        "source_summaries": source_summaries,
        "cluster_signals": cluster_signals,
        "comparative_metrics": build_cluster_comparative_metrics(members, editorial_rows),
        "confidence_note": confidence_note,
        "scope_note": (
            "This summary describes editorial patterns inside this story "
            "cluster only, not the outlets overall."
        ),
    }


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


def build_review_flags(
    *,
    analysis_status: str,
    bias_label: str,
    bias_confidence: float,
    evidence_spans: list[dict],
    unclear_reasons: list[str],
    editorial_applicability: str,
) -> dict[str, bool]:
    missing_evidence = analysis_status == "completed" and not evidence_spans
    low_confidence = analysis_status == "completed" and bias_confidence < 0.45
    failed_analysis = analysis_status == "failed"
    unclear_bias = bias_label == "unclear"
    provider_missing = "provider_missing" in unclear_reasons
    mapping_loss = "mapping_loss" in unclear_reasons or "repair_data_loss" in unclear_reasons
    out_of_domain = editorial_applicability == "out_of_domain"
    pending_analysis = analysis_status == "pending"
    needs_review = any(
        [
            missing_evidence,
            low_confidence,
            failed_analysis,
            unclear_bias,
            provider_missing,
            mapping_loss,
            out_of_domain,
            pending_analysis,
        ]
    )
    return {
        "missing_evidence": missing_evidence,
        "low_confidence": low_confidence,
        "failed_analysis": failed_analysis,
        "unclear_bias": unclear_bias,
        "provider_missing": provider_missing,
        "mapping_loss": mapping_loss,
        "out_of_domain": out_of_domain,
        "pending_analysis": pending_analysis,
        "needs_review": needs_review,
    }


def parse_json_object(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_json_list(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def parse_json_scalar_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]
