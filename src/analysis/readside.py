"""Read-side queries that shape cluster data for the API, not raw ORM dumps."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from src.analysis.orm_models import (
    ArticleEditorialAnalysisORM,
    ArticleTagORM,
    ClusterEntityORM,
    ClusterMemberORM,
    EntityMentionORM,
    EntityORM,
    StoryClusterORM,
    TagORM,
)
from src.persistence.orm import ArticleORM


@dataclass
class ClusterListFilters:
    limit: int = 20
    offset: int = 0
    source: str | None = None
    tag_code: str | None = None
    entity_slug: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = None


@dataclass
class EditorialAnalysisListFilters:
    limit: int = 20
    offset: int = 0
    source: str | None = None
    bias_label: str | None = None
    article_type: str | None = None
    analysis_status: str | None = None
    tone_emotional: str | None = None
    opinionatedness: str | None = None
    min_bias_confidence: float | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort: str = "published_at_desc"


def load_article_editorial_analysis(session: Session, article_id: int) -> dict | None:
    row = session.execute(
        select(ArticleORM, ArticleEditorialAnalysisORM)
        .join(ArticleEditorialAnalysisORM, ArticleEditorialAnalysisORM.article_id == ArticleORM.id)
        .where(ArticleEditorialAnalysisORM.article_id == article_id)
    ).one_or_none()
    if row is None:
        return None
    article, analysis = row
    evidence_spans = json.loads(analysis.evidence_spans_json or "[]")
    unclear_reasons = _parse_json_scalar_list(analysis.unclear_reasons_json)
    review_flags = _build_review_flags(
        analysis_status=analysis.analysis_status,
        bias_label=analysis.bias_label,
        bias_confidence=float(analysis.bias_confidence),
        evidence_spans=evidence_spans,
        unclear_reasons=unclear_reasons,
        editorial_applicability=analysis.editorial_applicability,
    )
    return {
        "article_id": analysis.article_id,
        "source": article.source,
        "section": article.section or "",
        "title": article.title,
        "url": article.url,
        "published_at": _iso(article.published_at),
        "summary": article.summary or "",
        "content_preview": (article.article_text or "")[:280],
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
        "editorial_applicability": analysis.editorial_applicability,
        "editorial_applicability_reason": analysis.editorial_applicability_reason,
        "provider_failure_class": analysis.provider_failure_class,
        "analysis_path": analysis.analysis_path,
        "unclear_reasons": unclear_reasons,
        "article_type_status": analysis.article_type_status,
        "bias_status": analysis.bias_status,
        "tone_emotional_status": analysis.tone_emotional_status,
        "tone_target_status": analysis.tone_target_status,
        "opinionatedness_status": analysis.opinionatedness_status,
        "sensationalism_status": analysis.sensationalism_status,
        "rhetorical_certainty_status": analysis.rhetorical_certainty_status,
        "framing_status": analysis.framing_status,
        "framing_devices": json.loads(analysis.framing_devices_json or "[]"),
        "evidence_spans": evidence_spans,
        "diagnostics": _parse_json_object(analysis.diagnostics_json),
        "rationale": analysis.rationale,
        "analysis_status": analysis.analysis_status,
        "failure_reason": analysis.failure_reason,
        "model_provider": analysis.model_provider,
        "model_name": analysis.model_name,
        "model_version": analysis.model_version,
        "prompt_version": analysis.prompt_version,
        "schema_version": analysis.schema_version,
        "content_hash": analysis.content_hash,
        "source_text_version": analysis.source_text_version,
        "analyzed_at": _iso(analysis.analyzed_at),
        "updated_at": _iso(analysis.updated_at),
        "review_flags": review_flags,
    }


def load_article_editorial_summary(session: Session, article_id: int) -> dict | None:
    row = session.execute(
        select(ArticleORM, ArticleEditorialAnalysisORM)
        .outerjoin(
            ArticleEditorialAnalysisORM,
            ArticleEditorialAnalysisORM.article_id == ArticleORM.id,
        )
        .where(ArticleORM.id == article_id)
    ).one_or_none()
    if row is None:
        return None
    article, analysis = row
    return _shape_product_editorial_summary(article.id, analysis)


def load_article_editorial_analysis_list(
    session: Session, filters: EditorialAnalysisListFilters
) -> tuple[list[dict], int]:
    stmt = _matching_editorial_analysis_stmt(filters)
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    sort_columns = _editorial_sort_columns(filters.sort)
    rows = session.execute(
        stmt.order_by(*sort_columns).offset(filters.offset).limit(filters.limit)
    ).all()
    items = []
    for article, analysis in rows:
        evidence_spans = _parse_json_list(analysis.evidence_spans_json if analysis else "[]")
        unclear_reasons = _parse_json_scalar_list(analysis.unclear_reasons_json) if analysis else []
        analysis_status = analysis.analysis_status if analysis else "pending"
        bias_label = analysis.bias_label if analysis else "unclear"
        bias_confidence = float(analysis.bias_confidence) if analysis else 0.0
        review_flags = _build_review_flags(
            analysis_status=analysis_status,
            bias_label=bias_label,
            bias_confidence=bias_confidence,
            evidence_spans=evidence_spans,
            unclear_reasons=unclear_reasons,
            editorial_applicability=analysis.editorial_applicability if analysis else "full",
        )
        items.append(
            {
                "article_id": article.id,
                "source": article.source,
                "section": article.section or "",
                "title": article.title,
                "url": article.url,
                "published_at": _iso(article.published_at),
                "summary": article.summary or "",
                "article_type": analysis.article_type if analysis else "unclear",
                "article_type_confidence": float(analysis.article_type_confidence)
                if analysis
                else 0.0,
                "editorial_applicability": analysis.editorial_applicability if analysis else "full",
                "provider_failure_class": analysis.provider_failure_class if analysis else "",
                "analysis_path": analysis.analysis_path if analysis else "",
                "unclear_reasons": unclear_reasons,
                "article_type_status": analysis.article_type_status if analysis else "",
                "bias_status": analysis.bias_status if analysis else "",
                "tone_emotional_status": analysis.tone_emotional_status if analysis else "",
                "opinionatedness_status": analysis.opinionatedness_status if analysis else "",
                "framing_status": analysis.framing_status if analysis else "",
                "bias_label": bias_label,
                "bias_score": float(analysis.bias_score) if analysis else 0.0,
                "bias_confidence": bias_confidence,
                "tone_emotional": analysis.tone_emotional if analysis else "unclear",
                "opinionatedness": analysis.opinionatedness if analysis else "unclear",
                "analysis_status": analysis_status,
                "rationale": analysis.rationale if analysis else "",
                "evidence_count": len(evidence_spans),
                "evidence_spans": evidence_spans[:2],
                "failure_reason": analysis.failure_reason if analysis else "",
                "analyzed_at": _iso(analysis.analyzed_at) if analysis else None,
                "review_flags": review_flags,
            }
        )
    return items, total


def load_story_clusters(session: Session, filters: ClusterListFilters) -> tuple[list[dict], int]:
    """Load one page of cluster cards plus the total count for the active filter set."""

    cluster_ids = _matching_cluster_ids_stmt(filters)
    total = session.execute(select(func.count()).select_from(cluster_ids.subquery())).scalar_one()
    ids = (
        session.execute(
            cluster_ids.order_by(
                StoryClusterORM.article_count.desc(),
                StoryClusterORM.source_count.desc(),
                StoryClusterORM.last_article_published_at.desc().nullslast(),
                StoryClusterORM.id.desc(),
            )
            .offset(filters.offset)
            .limit(filters.limit)
        )
        .scalars()
        .all()
    )
    if not ids:
        return [], total
    payload, _ = load_story_clusters_for_ids(session, ids)
    return payload, total


def load_story_cluster_detail(session: Session, cluster_id: int) -> dict | None:
    """Load one cluster card plus its ordered member article payloads."""

    cluster = session.execute(
        select(StoryClusterORM).where(StoryClusterORM.id == cluster_id)
    ).scalar_one_or_none()
    if cluster is None:
        return None
    cluster_payload, _ = load_story_clusters_for_ids(session, [cluster_id])
    members = session.execute(
        select(
            ClusterMemberORM.article_id,
            ClusterMemberORM.membership_score,
            ClusterMemberORM.membership_reason_json,
            ArticleORM.source,
            ArticleORM.title,
            ArticleORM.url,
            ArticleORM.published_at,
            ArticleORM.section,
            ArticleORM.summary,
        )
        .join(ArticleORM, ArticleORM.id == ClusterMemberORM.article_id)
        .where(ClusterMemberORM.cluster_id == cluster_id)
        .order_by(
            ArticleORM.published_at.desc().nullslast(), ClusterMemberORM.membership_score.desc()
        )
    ).all()
    article_ids = [row.article_id for row in members]
    tags_by_article = _load_article_tags(session, article_ids)
    entities_by_article = _load_article_entities(session, article_ids)
    editorial_rows = _load_editorial_rows_for_articles(session, article_ids)
    return {
        "cluster": cluster_payload[0],
        "members": [
            {
                "article_id": row.article_id,
                "source": row.source,
                "title": row.title,
                "url": row.url,
                "published_at": _iso(row.published_at),
                "section": row.section or "",
                "summary": row.summary or "",
                "membership_score": round(float(row.membership_score), 4),
                "membership_diagnostics": _parse_json_object(row.membership_reason_json),
                "tags": tags_by_article.get(row.article_id, []),
                "entities": entities_by_article.get(row.article_id, []),
                "editorial_preview": _shape_member_editorial_preview(
                    editorial_rows.get(row.article_id)
                ),
            }
            for row in members
        ],
        "editorial_summary": _build_cluster_editorial_summary(members, editorial_rows),
    }


def load_story_clusters_for_ids(session: Session, ids: list[int]) -> tuple[list[dict], int]:
    if not ids:
        return [], 0
    clusters = {
        row.id: row
        for row in session.execute(
            select(StoryClusterORM).where(StoryClusterORM.id.in_(ids))
        ).scalars()
    }
    primary_tags = {row.id: row for row in session.execute(select(TagORM)).scalars()}
    source_rows = session.execute(
        select(ClusterMemberORM.cluster_id, ArticleORM.source)
        .join(ArticleORM, ArticleORM.id == ClusterMemberORM.article_id)
        .where(ClusterMemberORM.cluster_id.in_(ids))
    ).all()
    sources_by_cluster: dict[int, list[str]] = {cluster_id: [] for cluster_id in ids}
    for cluster_id, source in source_rows:
        bucket = sources_by_cluster.setdefault(cluster_id, [])
        if source not in bucket:
            bucket.append(source)
    entity_rows = session.execute(
        select(
            ClusterEntityORM.cluster_id,
            EntityORM.id,
            EntityORM.slug,
            EntityORM.canonical_name,
            EntityORM.entity_type,
            ClusterEntityORM.article_coverage_count,
            ClusterEntityORM.mention_count,
            ClusterEntityORM.aggregate_relevance_score,
        )
        .join(EntityORM, EntityORM.id == ClusterEntityORM.entity_id)
        .where(ClusterEntityORM.cluster_id.in_(ids))
        .order_by(
            ClusterEntityORM.cluster_id,
            ClusterEntityORM.article_coverage_count.desc(),
            ClusterEntityORM.aggregate_relevance_score.desc(),
            ClusterEntityORM.mention_count.desc(),
        )
    ).all()
    entities_by_cluster: dict[int, list[dict]] = {cluster_id: [] for cluster_id in ids}
    for row in entity_rows:
        items = entities_by_cluster.setdefault(row.cluster_id, [])
        if len(items) >= 5:
            continue
        items.append(
            {
                "entity_id": row.id,
                "slug": row.slug,
                "name": row.canonical_name,
                "entity_type": row.entity_type,
                "article_coverage_count": row.article_coverage_count,
                "mention_count": row.mention_count,
            }
        )
    payload = []
    for cluster_id in ids:
        cluster = clusters.get(cluster_id)
        if cluster is None:
            continue
        primary_tag = primary_tags.get(cluster.primary_tag_id) if cluster.primary_tag_id else None
        payload.append(
            {
                "id": cluster.id,
                "cluster_key": cluster.cluster_key,
                "status": cluster.status,
                "cluster_type": cluster.cluster_type,
                "summary_headline": cluster.summary_headline,
                "summary_text": cluster.summary_text,
                "article_count": cluster.article_count,
                "source_count": cluster.source_count,
                "first_article_published_at": _iso(cluster.first_article_published_at),
                "last_article_published_at": _iso(cluster.last_article_published_at),
                "sources": sorted(sources_by_cluster.get(cluster_id, [])),
                "primary_tag": (
                    {
                        "tag_code": primary_tag.tag_code,
                        "display_name": primary_tag.display_name,
                        "tag_group": primary_tag.tag_group,
                    }
                    if primary_tag
                    else None
                ),
                "top_entities": entities_by_cluster.get(cluster_id, []),
            }
        )
    return payload, len(payload)


def _load_editorial_rows_for_articles(
    session: Session, article_ids: list[int]
) -> dict[int, ArticleEditorialAnalysisORM]:
    if not article_ids:
        return {}
    rows = session.execute(
        select(ArticleEditorialAnalysisORM).where(ArticleEditorialAnalysisORM.article_id.in_(article_ids))
    ).scalars()
    return {row.article_id: row for row in rows}


def _shape_product_editorial_summary(
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
            "review_flags": _build_review_flags(
                analysis_status="pending",
                bias_label="unclear",
                bias_confidence=0.0,
                evidence_spans=[],
                unclear_reasons=[],
                editorial_applicability="full",
            ),
            "diagnostics_summary": None,
        }
    evidence_spans = _parse_json_list(analysis.evidence_spans_json)
    unclear_reasons = _parse_json_scalar_list(analysis.unclear_reasons_json)
    diagnostics = _parse_json_object(analysis.diagnostics_json)
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
        "framing_devices": _parse_json_scalar_list(analysis.framing_devices_json),
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
        "review_flags": _build_review_flags(
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


def _shape_member_editorial_preview(analysis: ArticleEditorialAnalysisORM | None) -> dict:
    summary = _shape_product_editorial_summary(getattr(analysis, "article_id", 0), analysis)
    return {
        "analysis_status": summary["analysis_status"],
        "article_type": summary["article_type"],
        "bias_label": summary["bias_label"],
        "bias_confidence": summary["bias_confidence"],
        "editorial_applicability": summary["editorial_applicability"],
        "review_flags": {
            "low_confidence": summary["review_flags"]["low_confidence"],
            "needs_review": summary["review_flags"]["needs_review"],
        },
    }


def _build_cluster_editorial_summary(
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
        summary = _shape_product_editorial_summary(member.article_id, analysis)
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
        "comparative_metrics": _build_cluster_comparative_metrics(members, editorial_rows),
        "confidence_note": confidence_note,
        "scope_note": (
            "This summary describes editorial patterns inside this story "
            "cluster only, not the outlets overall."
        ),
    }


def _build_cluster_comparative_metrics(
    members, editorial_rows: dict[int, ArticleEditorialAnalysisORM]
) -> dict:
    minimum_articles_per_source = 2
    source_articles: dict[str, list[dict]] = defaultdict(list)

    for member in members:
        analysis = editorial_rows.get(member.article_id)
        if analysis is None:
            continue
        review_flags = _build_review_flags(
            analysis_status=analysis.analysis_status,
            bias_label=analysis.bias_label,
            bias_confidence=float(analysis.bias_confidence),
            evidence_spans=_parse_json_list(analysis.evidence_spans_json),
            unclear_reasons=_parse_json_scalar_list(analysis.unclear_reasons_json),
            editorial_applicability=analysis.editorial_applicability,
        )
        source_articles[member.source].append(
            {
                "article_id": member.article_id,
                "analysis": analysis,
                "review_flags": review_flags,
                "framing_devices": _parse_json_scalar_list(analysis.framing_devices_json),
            }
        )

    included_sources = []
    source_metrics = []
    source_payloads: dict[str, dict] = {}
    eligible_sources: list[str] = []

    for source in sorted(source_articles):
        rows = source_articles[source]
        usable_rows = [
            row for row in rows if _is_editorial_row_usable_for_dimension(row["analysis"])
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
            eligible_sources.append(source)
        else:
            eligibility = "eligible"
            comparison_note = "Enough usable cluster-scoped coverage for cautious comparison."
            eligible_sources.append(source)

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

        metric_payload = _compute_source_dimension_index(source, usable_rows, eligibility)
        source_metrics.append(metric_payload)
        source_payloads[source] = {
            "source": source,
            "eligibility": eligibility,
            "metric_payload": metric_payload,
            "usable_rows": usable_rows,
        }

    divergence_signals = _build_divergence_signals(source_payloads)
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


def _compute_source_dimension_index(source: str, usable_rows: list[dict], eligibility: str) -> dict:
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

    opinionatedness_index, opinionated_support = _average_dimension_index(
        usable_rows,
        value_getter=lambda row: _map_opinionatedness(row["analysis"].opinionatedness),
        status_getter=lambda row: row["analysis"].opinionatedness_status,
        min_support=2,
    )
    if opinionatedness_index is None:
        metric_notes.append(
            "Opinionatedness stayed mixed or under-supported, so the index is hidden."
        )

    emotional_tone_index, tone_support = _average_dimension_index(
        usable_rows,
        value_getter=lambda row: _map_tone(row["analysis"].tone_emotional),
        status_getter=lambda row: row["analysis"].tone_emotional_status,
        min_support=2,
    )
    if emotional_tone_index is None:
        metric_notes.append("Tone stayed mixed or under-supported, so the index is hidden.")

    bias_direction_index, bias_support = _average_dimension_index(
        usable_rows,
        value_getter=lambda row: _map_bias_direction(row["analysis"].bias_label),
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


def _build_divergence_signals(source_payloads: dict[str, dict]) -> list[dict]:
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
                    "example_article_ids": _example_article_ids_for_dimension(
                        leading["usable_rows"], dimension
                    ),
                }
                if best_signal is None or candidate["delta"] > best_signal["delta"]:
                    best_signal = candidate
        if best_signal is not None:
            signals.append(best_signal)
    return signals


def _example_article_ids_for_dimension(usable_rows: list[dict], dimension: str) -> list[int]:
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


def _average_dimension_index(
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


def _is_editorial_row_usable_for_dimension(analysis: ArticleEditorialAnalysisORM) -> bool:
    return (
        analysis.analysis_status == "completed"
        and analysis.editorial_applicability != "out_of_domain"
    )


def _map_opinionatedness(value: str) -> float | None:
    return {"low": 0.0, "mixed": 0.5, "high": 1.0}.get(value)


def _map_tone(value: str) -> float | None:
    return {
        "measured": 0.0,
        "somewhat_emotional": 0.5,
        "critical": 1.0,
        "emotional": 1.0,
    }.get(value)


def _map_bias_direction(value: str) -> float | None:
    return {
        "left": -1.0,
        "center_left": -0.5,
        "unclear": 0.0,
        "center": 0.0,
        "center_right": 0.5,
        "right": 1.0,
    }.get(value)


def load_story_cluster_filters(session: Session, filters: ClusterListFilters) -> dict:
    cluster_ids = session.execute(_matching_cluster_ids_stmt(filters)).scalars().all()
    if not cluster_ids:
        return {"sources": [], "tags": [], "entities": []}
    sources = session.execute(
        select(ArticleORM.source, func.count(func.distinct(ClusterMemberORM.cluster_id)))
        .join(ClusterMemberORM, ClusterMemberORM.article_id == ArticleORM.id)
        .where(ClusterMemberORM.cluster_id.in_(cluster_ids))
        .group_by(ArticleORM.source)
        .order_by(func.count(func.distinct(ClusterMemberORM.cluster_id)).desc(), ArticleORM.source)
    ).all()
    tags = session.execute(
        select(
            TagORM.tag_code,
            TagORM.display_name,
            func.count(func.distinct(ClusterMemberORM.cluster_id)),
        )
        .join(ArticleTagORM, ArticleTagORM.tag_id == TagORM.id)
        .join(ClusterMemberORM, ClusterMemberORM.article_id == ArticleTagORM.article_id)
        .where(ClusterMemberORM.cluster_id.in_(cluster_ids))
        .group_by(TagORM.tag_code, TagORM.display_name)
        .order_by(func.count(func.distinct(ClusterMemberORM.cluster_id)).desc(), TagORM.tag_code)
    ).all()
    entities = session.execute(
        select(
            EntityORM.slug,
            EntityORM.canonical_name,
            EntityORM.entity_type,
            func.count(func.distinct(ClusterEntityORM.cluster_id)),
        )
        .join(ClusterEntityORM, ClusterEntityORM.entity_id == EntityORM.id)
        .where(ClusterEntityORM.cluster_id.in_(cluster_ids))
        .group_by(EntityORM.slug, EntityORM.canonical_name, EntityORM.entity_type)
        .order_by(
            func.count(func.distinct(ClusterEntityORM.cluster_id)).desc(), EntityORM.canonical_name
        )
        .limit(50)
    ).all()
    return {
        "sources": [
            {"value": source, "label": source, "count": count} for source, count in sources
        ],
        "tags": [
            {"value": tag_code, "label": display_name, "count": count}
            for tag_code, display_name, count in tags
        ],
        "entities": [
            {
                "slug": slug,
                "name": name,
                "entity_type": entity_type,
                "count": count,
            }
            for slug, name, entity_type, count in entities
        ],
    }


def _matching_editorial_analysis_stmt(filters: EditorialAnalysisListFilters):
    stmt = select(ArticleORM, ArticleEditorialAnalysisORM).outerjoin(
        ArticleEditorialAnalysisORM, ArticleEditorialAnalysisORM.article_id == ArticleORM.id
    )
    conditions = []
    if filters.source:
        conditions.append(ArticleORM.source == filters.source)
    if filters.bias_label:
        conditions.append(ArticleEditorialAnalysisORM.bias_label == filters.bias_label)
    if filters.article_type:
        conditions.append(ArticleEditorialAnalysisORM.article_type == filters.article_type)
    if filters.tone_emotional:
        conditions.append(ArticleEditorialAnalysisORM.tone_emotional == filters.tone_emotional)
    if filters.opinionatedness:
        conditions.append(ArticleEditorialAnalysisORM.opinionatedness == filters.opinionatedness)
    if filters.min_bias_confidence is not None:
        conditions.append(
            ArticleEditorialAnalysisORM.bias_confidence >= filters.min_bias_confidence
        )
    if filters.date_from:
        conditions.append(
            ArticleORM.published_at >= datetime.combine(filters.date_from, datetime.min.time())
        )
    if filters.date_to:
        conditions.append(
            ArticleORM.published_at <= datetime.combine(filters.date_to, datetime.max.time())
        )
    if filters.analysis_status:
        if filters.analysis_status == "pending":
            conditions.append(
                or_(
                    ArticleEditorialAnalysisORM.id.is_(None),
                    ArticleEditorialAnalysisORM.analysis_status == "pending",
                )
            )
        else:
            conditions.append(
                ArticleEditorialAnalysisORM.analysis_status == filters.analysis_status
            )
    if conditions:
        stmt = stmt.where(and_(*conditions))
    return stmt


def _editorial_sort_columns(sort: str):
    mapping = {
        "published_at_asc": [ArticleORM.published_at.asc().nullsfirst(), ArticleORM.id.asc()],
        "published_at_desc": [ArticleORM.published_at.desc().nullslast(), ArticleORM.id.desc()],
        "analyzed_at_desc": [
            ArticleEditorialAnalysisORM.analyzed_at.desc().nullslast(),
            ArticleORM.published_at.desc().nullslast(),
        ],
        "bias_score_asc": [
            ArticleEditorialAnalysisORM.bias_score.asc().nullsfirst(),
            ArticleORM.id.asc(),
        ],
        "bias_score_desc": [
            ArticleEditorialAnalysisORM.bias_score.desc().nullslast(),
            ArticleORM.id.desc(),
        ],
        "bias_confidence_desc": [
            ArticleEditorialAnalysisORM.bias_confidence.desc().nullslast(),
            ArticleORM.id.desc(),
        ],
    }
    return mapping.get(sort, mapping["published_at_desc"])


def _matching_cluster_ids_stmt(filters: ClusterListFilters) -> Select:
    stmt = (
        select(StoryClusterORM.id)
        .join(ClusterMemberORM, ClusterMemberORM.cluster_id == StoryClusterORM.id)
        .join(ArticleORM, ArticleORM.id == ClusterMemberORM.article_id)
        .group_by(
            StoryClusterORM.id,
            StoryClusterORM.article_count,
            StoryClusterORM.source_count,
            StoryClusterORM.last_article_published_at,
        )
    )
    if filters.source:
        stmt = stmt.where(ArticleORM.source == filters.source)
    if filters.tag_code:
        stmt = stmt.join(ArticleTagORM, ArticleTagORM.article_id == ArticleORM.id).join(
            TagORM, TagORM.id == ArticleTagORM.tag_id
        )
        stmt = stmt.where(TagORM.tag_code == filters.tag_code)
    if filters.entity_slug:
        stmt = stmt.join(EntityMentionORM, EntityMentionORM.article_id == ArticleORM.id).join(
            EntityORM, EntityORM.id == EntityMentionORM.entity_id
        )
        stmt = stmt.where(EntityORM.slug == filters.entity_slug)
    if filters.date_from:
        stmt = stmt.where(StoryClusterORM.last_article_published_at >= filters.date_from)
    if filters.date_to:
        stmt = stmt.where(
            StoryClusterORM.first_article_published_at
            < datetime.combine(filters.date_to, datetime.max.time())
        )
    if filters.search:
        term = f"%{filters.search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(StoryClusterORM.summary_headline).like(term),
                func.lower(StoryClusterORM.summary_text).like(term),
                func.lower(ArticleORM.title).like(term),
            )
        )
    return stmt


def _load_article_tags(session: Session, article_ids: list[int]) -> dict[int, list[dict]]:
    if not article_ids:
        return {}
    rows = session.execute(
        select(ArticleTagORM.article_id, TagORM.tag_code, TagORM.display_name, TagORM.tag_group)
        .join(TagORM, TagORM.id == ArticleTagORM.tag_id)
        .where(ArticleTagORM.article_id.in_(article_ids))
        .order_by(ArticleTagORM.article_id, ArticleTagORM.is_primary.desc(), TagORM.sort_order)
    ).all()
    result: dict[int, list[dict]] = {}
    for article_id, tag_code, display_name, tag_group in rows:
        result.setdefault(article_id, []).append(
            {"tag_code": tag_code, "display_name": display_name, "tag_group": tag_group}
        )
    return result


def _load_article_entities(session: Session, article_ids: list[int]) -> dict[int, list[dict]]:
    if not article_ids:
        return {}
    rows = session.execute(
        select(
            EntityMentionORM.article_id,
            EntityORM.id,
            EntityORM.slug,
            EntityORM.canonical_name,
            EntityORM.entity_type,
            EntityMentionORM.mention_count,
            EntityMentionORM.relevance_score,
        )
        .join(EntityORM, EntityORM.id == EntityMentionORM.entity_id)
        .where(EntityMentionORM.article_id.in_(article_ids))
        .order_by(
            EntityMentionORM.article_id,
            EntityMentionORM.relevance_score.desc(),
            EntityMentionORM.mention_count.desc(),
        )
    ).all()
    result: dict[int, list[dict]] = {}
    for row in rows:
        items = result.setdefault(row.article_id, [])
        if any(existing["entity_id"] == row.id for existing in items):
            continue
        if len(items) >= 5:
            continue
        items.append(
            {
                "entity_id": row.id,
                "slug": row.slug,
                "name": row.canonical_name,
                "entity_type": row.entity_type,
                "article_coverage_count": 1,
                "mention_count": row.mention_count,
            }
        )
    return result


def _build_review_flags(
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


def _parse_json_object(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _parse_json_list(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _parse_json_scalar_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
