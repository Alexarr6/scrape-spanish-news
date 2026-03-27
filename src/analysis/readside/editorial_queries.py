from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from src.analysis.editorial.orm import ArticleEditorialAnalysisORM
from src.analysis.readside.common import iso_datetime
from src.analysis.readside.editorial_summary import (
    build_review_flags,
    parse_json_list,
    parse_json_object,
    parse_json_scalar_list,
    shape_product_editorial_summary,
)
from src.analysis.readside.filters import EditorialAnalysisListFilters
from src.persistence.orm import ArticleORM


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
    unclear_reasons = parse_json_scalar_list(analysis.unclear_reasons_json)
    review_flags = build_review_flags(
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
        "published_at": iso_datetime(article.published_at),
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
        "diagnostics": parse_json_object(analysis.diagnostics_json),
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
        "analyzed_at": iso_datetime(analysis.analyzed_at),
        "updated_at": iso_datetime(analysis.updated_at),
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
    return shape_product_editorial_summary(article.id, analysis)


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
        evidence_spans = parse_json_list(analysis.evidence_spans_json if analysis else "[]")
        unclear_reasons = parse_json_scalar_list(analysis.unclear_reasons_json) if analysis else []
        analysis_status = analysis.analysis_status if analysis else "pending"
        bias_label = analysis.bias_label if analysis else "unclear"
        bias_confidence = float(analysis.bias_confidence) if analysis else 0.0
        review_flags = build_review_flags(
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
                "published_at": iso_datetime(article.published_at),
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
                "analyzed_at": iso_datetime(analysis.analyzed_at) if analysis else None,
                "review_flags": review_flags,
            }
        )
    return items, total


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
