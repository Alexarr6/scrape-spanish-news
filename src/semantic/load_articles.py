from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.persistence.db import create_postgres_engine, make_session
from src.persistence.orm import ArticleORM
from src.semantic.contracts import SemanticArticle


def load_articles(*, database_url: str, limit: int) -> list[SemanticArticle]:
    engine = create_postgres_engine(database_url)
    with make_session(engine) as session:
        return _load_articles(session=session, limit=limit)


def _load_articles(*, session: Session, limit: int) -> list[SemanticArticle]:
    stmt: Select[tuple[ArticleORM]] = (
        select(ArticleORM)
        .order_by(ArticleORM.published_at.desc().nullslast(), ArticleORM.id.desc())
        .limit(limit)
    )
    rows = session.execute(stmt).scalars().all()
    return [
        SemanticArticle(
            article_id=row.id,
            source=row.source,
            title=row.title,
            url=row.url,
            published_at=row.published_at.isoformat() if row.published_at else "",
            section=row.section or "",
            summary=row.summary or "",
            article_text=row.article_text or "",
        )
        for row in rows
    ]
