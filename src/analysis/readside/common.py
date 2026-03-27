from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.editorial.orm import ArticleEditorialAnalysisORM
from src.analysis.store.models import ArticleTagORM, EntityMentionORM, EntityORM, TagORM


def load_editorial_rows_for_articles(
    session: Session, article_ids: list[int]
) -> dict[int, ArticleEditorialAnalysisORM]:
    if not article_ids:
        return {}
    rows = session.execute(
        select(ArticleEditorialAnalysisORM).where(ArticleEditorialAnalysisORM.article_id.in_(article_ids))
    ).scalars()
    return {row.article_id: row for row in rows}


def load_article_tags(session: Session, article_ids: list[int]) -> dict[int, list[dict]]:
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


def load_article_entities(session: Session, article_ids: list[int]) -> dict[int, list[dict]]:
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


def iso_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
