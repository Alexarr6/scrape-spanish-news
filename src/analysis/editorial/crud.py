from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.editorial.orm import ArticleEditorialAnalysisORM


class EditorialAnalysisCRUD:
    """Synchronous CRUD boundary for editorial analysis rows.

    FastCRUD is attractive here, but the current repository uses sync SQLAlchemy sessions
    end-to-end. This module establishes the target `core/orm/crud` shape first so the
    storage layer can be swapped later without reshaping the rest of the code again.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_article_id(self, article_id: int) -> ArticleEditorialAnalysisORM | None:
        return self.session.execute(
            select(ArticleEditorialAnalysisORM).where(
                ArticleEditorialAnalysisORM.article_id == article_id
            )
        ).scalar_one_or_none()

    def save(self, analysis: ArticleEditorialAnalysisORM) -> ArticleEditorialAnalysisORM:
        self.session.add(analysis)
        self.session.flush()
        self.session.refresh(analysis)
        return analysis
