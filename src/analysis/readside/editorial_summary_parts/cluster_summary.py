from __future__ import annotations

from collections import Counter, defaultdict

from src.analysis.readside.editorial_summary_parts.comparative_metrics import (
    build_cluster_comparative_metrics,
)
from src.analysis.readside.editorial_summary_parts.product_summary import (
    shape_product_editorial_summary,
)
from src.analysis.store.models import ArticleEditorialAnalysisORM


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
