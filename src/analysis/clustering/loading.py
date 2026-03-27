from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.shared.contracts import ArticleAnalysisRead
from src.analysis.shared.types import EnrichedArticle
from src.analysis.store.models import (
    ArticleAnalysisORM,
    ArticleMatchingSelectionORM,
    ArticleTagORM,
    EntityMentionORM,
    EntityORM,
    TagORM,
)
from src.persistence.core import ArticleRead
from src.persistence.orm import ArticleORM


def load_enriched_articles(
    session: Session,
    *,
    days_back: int,
    limit: int,
    corpus: Literal["raw", "matching"] = "matching",
) -> list[EnrichedArticle]:
    cutoff = datetime.now(UTC) - timedelta(days=days_back)
    stmt = (
        select(ArticleORM, ArticleAnalysisORM)
        .join(ArticleAnalysisORM, ArticleAnalysisORM.article_id == ArticleORM.id)
        .where(ArticleORM.published_at.is_not(None), ArticleORM.published_at >= cutoff)
    )
    if corpus == "matching":
        stmt = (
            stmt.join(
                ArticleMatchingSelectionORM,
                ArticleMatchingSelectionORM.article_id == ArticleORM.id,
            )
            .where(ArticleMatchingSelectionORM.selection_rank.is_not(None))
            .order_by(
                ArticleMatchingSelectionORM.local_published_date.desc().nullslast(),
                ArticleMatchingSelectionORM.selection_rank.asc().nullslast(),
                ArticleORM.published_at.desc(),
            )
            .limit(limit)
        )
    else:
        stmt = stmt.order_by(ArticleORM.published_at.desc()).limit(limit)
    rows = session.execute(stmt).all()
    tag_lookup = {row.id: row.tag_code for row in session.execute(select(TagORM)).scalars()}
    result: list[EnrichedArticle] = []
    for article_row, analysis_row in rows:
        article = ArticleRead.model_validate(article_row)
        analysis = ArticleAnalysisRead.model_validate(analysis_row)
        article_tags = (
            session.execute(select(ArticleTagORM).where(ArticleTagORM.article_id == article.id))
            .scalars()
            .all()
        )
        tag_codes = [tag_lookup[tag.tag_id] for tag in article_tags if tag.tag_id in tag_lookup]
        mentions = session.execute(
            select(EntityMentionORM, EntityORM.slug)
            .join(EntityORM, EntityORM.id == EntityMentionORM.entity_id)
            .where(EntityMentionORM.article_id == article.id)
        ).all()
        entity_slugs = [slug for _, slug in mentions]
        key_phrases = json.loads(analysis.key_phrases_json)
        result.append(
            EnrichedArticle(
                article=article,
                analysis=analysis,
                tag_codes=tag_codes,
                entity_slugs=entity_slugs,
                key_phrases=key_phrases,
            )
        )
    return result
