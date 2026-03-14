from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.persistence.contracts import ArticleCreate, ArticleRead, ArticleUpdate, IngestResult
from src.persistence.orm_models import ArticleORM


class ArticleCRUD:
    """FastCRUD-style access layer with explicit create/read/update/delete methods."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, limit: int = 100, offset: int = 0) -> list[ArticleRead]:
        stmt: Select[tuple[ArticleORM]] = (
            select(ArticleORM).order_by(ArticleORM.published_at.desc()).offset(offset).limit(limit)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [ArticleRead.model_validate(row) for row in rows]

    def get(self, article_id: int) -> ArticleRead | None:
        row = self.session.get(ArticleORM, article_id)
        if row is None:
            return None
        return ArticleRead.model_validate(row)

    def upsert(self, payload: ArticleCreate) -> tuple[ArticleRead, str]:
        existing = self.session.execute(
            select(ArticleORM).where(
                ArticleORM.source == payload.source,
                ArticleORM.url == str(payload.url),
            )
        ).scalar_one_or_none()

        if existing is None:
            row = ArticleORM(**payload.model_dump(mode="json"))
            self.session.add(row)
            self.session.commit()
            self.session.refresh(row)
            return ArticleRead.model_validate(row), "inserted"

        mutable_fields = (
            "title",
            "published_at",
            "scraped_at",
            "section",
            "author",
            "summary",
            "article_text",
            "tags",
        )
        changed = False
        payload_data = payload.model_dump(mode="json")
        for field in mutable_fields:
            new_value = payload_data[field]
            if getattr(existing, field) != new_value:
                setattr(existing, field, new_value)
                changed = True

        if not changed:
            return ArticleRead.model_validate(existing), "unchanged"

        self.session.commit()
        self.session.refresh(existing)
        return ArticleRead.model_validate(existing), "updated"

    def update(self, article_id: int, payload: ArticleUpdate) -> ArticleRead | None:
        row = self.session.get(ArticleORM, article_id)
        if row is None:
            return None

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, key, value)

        self.session.commit()
        self.session.refresh(row)
        return ArticleRead.model_validate(row)

    def delete(self, article_id: int) -> bool:
        row = self.session.get(ArticleORM, article_id)
        if row is None:
            return False
        self.session.delete(row)
        self.session.commit()
        return True

    def ingest_many(self, rows: list[ArticleCreate]) -> IngestResult:
        result = IngestResult()
        for row in rows:
            try:
                _, status = self.upsert(row)
                if status == "inserted":
                    result.inserted += 1
                elif status == "updated":
                    result.updated += 1
                else:
                    result.unchanged += 1
            except Exception:
                self.session.rollback()
                result.errors += 1
        return result
