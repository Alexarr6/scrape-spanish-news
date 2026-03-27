from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.analysis.editorial.orm import ArticleEditorialAnalysisORM
from src.persistence.orm import ArticleORM


@dataclass
class EditorialSelectionFilters:
    days_back: int = 2
    limit: int = 100
    status: str = "pending"
    article_ids: list[int] | None = None
    source: str | None = None
    published_from: date | None = None
    published_to: date | None = None
    batch_size: int | None = None


def effective_status(*, status: str, reprocess: bool, article_ids: list[int] | None) -> str:
    return "any" if reprocess and status == "pending" and not article_ids else status


def select_candidate_articles(
    session: Session,
    filters: EditorialSelectionFilters,
) -> list[ArticleORM]:
    stmt = select(ArticleORM).outerjoin(
        ArticleEditorialAnalysisORM,
        ArticleEditorialAnalysisORM.article_id == ArticleORM.id,
    )
    if filters.article_ids:
        stmt = stmt.where(ArticleORM.id.in_(filters.article_ids))
    else:
        cutoff = datetime.now(UTC) - timedelta(days=filters.days_back)
        stmt = stmt.where(ArticleORM.published_at.is_not(None), ArticleORM.published_at >= cutoff)
        if filters.source:
            stmt = stmt.where(ArticleORM.source == filters.source)
        if filters.published_from:
            stmt = stmt.where(
                ArticleORM.published_at
                >= datetime.combine(filters.published_from, datetime.min.time())
            )
        if filters.published_to:
            stmt = stmt.where(
                ArticleORM.published_at
                <= datetime.combine(filters.published_to, datetime.max.time())
            )
        if filters.status == "pending":
            stmt = stmt.where(
                or_(
                    ArticleEditorialAnalysisORM.id.is_(None),
                    ArticleEditorialAnalysisORM.analysis_status == "pending",
                )
            )
        elif filters.status == "failed":
            stmt = stmt.where(ArticleEditorialAnalysisORM.analysis_status == "failed")
        elif filters.status == "completed":
            stmt = stmt.where(ArticleEditorialAnalysisORM.analysis_status == "completed")
        elif filters.status == "any":
            pass
        else:
            raise ValueError(f"Unsupported editorial analysis status: {filters.status}")
    return (
        session.execute(stmt.order_by(ArticleORM.published_at.desc()).limit(filters.limit))
        .scalars()
        .all()
    )


def should_skip_existing(
    analysis: ArticleEditorialAnalysisORM | None,
    *,
    content_hash: str,
    reprocess: bool,
) -> bool:
    return bool(
        analysis
        and not reprocess
        and analysis.content_hash == content_hash
        and analysis.analysis_status == "completed"
    )


def selection_status_counts(
    session: Session,
    *,
    days_back: int,
    limit: int,
    article_ids: list[int] | None = None,
    source: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
    batch_size: int | None = None,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for status in ("pending", "failed", "completed", "any"):
        rows = select_candidate_articles(
            session,
            EditorialSelectionFilters(
                days_back=days_back,
                limit=limit,
                status=status,
                article_ids=article_ids,
                source=source,
                published_from=published_from,
                published_to=published_to,
                batch_size=batch_size,
            ),
        )
        counts[status] = len(rows[:batch_size] if batch_size else rows)
    return counts
