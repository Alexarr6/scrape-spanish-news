from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.persistence.contracts import ArticleCreate
from src.persistence.crud import ArticleCRUD
from src.persistence.orm_models import ArticleORM, Base


class FlushExplodesOnce(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._flush_count = 0

    def flush(self, *args, **kwargs):
        self._flush_count += 1
        if self._flush_count == 2:
            raise SQLAlchemyError("boom during batch flush")
        return super().flush(*args, **kwargs)


def _payload(*, title: str = "Title", source: str = "elpais", url: str = "https://elpais.com/a") -> ArticleCreate:
    now = datetime(2026, 3, 15, 12, 0)
    return ArticleCreate(
        source=source,
        title=title,
        url=url,
        published_at=now,
        scraped_at=now,
        section="politica",
        author="Reporter",
        summary="Summary",
        article_text="Body",
        tags="tag1,tag2",
    )


def _session(session_cls: type[Session] = Session) -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return session_cls(engine)


def test_upsert_inserts_new_article():
    session = _session()
    crud = ArticleCRUD(session)

    article, status = crud.upsert(_payload())

    assert status == "inserted"
    assert article.id > 0
    assert session.scalar(select(ArticleORM.id).where(ArticleORM.source == "elpais")) == article.id



def test_upsert_updates_existing_article():
    session = _session()
    crud = ArticleCRUD(session)
    original, _ = crud.upsert(_payload())

    updated, status = crud.upsert(_payload(title="Updated title"))

    assert status == "updated"
    assert updated.id == original.id
    assert updated.title == "Updated title"
    row = session.get(ArticleORM, original.id)
    assert row is not None
    assert row.title == "Updated title"



def test_upsert_is_idempotent_when_payload_is_unchanged():
    session = _session()
    crud = ArticleCRUD(session)
    original, _ = crud.upsert(_payload())

    repeated, status = crud.upsert(_payload())

    assert status == "unchanged"
    assert repeated.id == original.id
    assert session.query(ArticleORM).count() == 1



def test_ingest_many_rolls_back_entire_batch_on_failure():
    session = _session(FlushExplodesOnce)
    crud = ArticleCRUD(session)

    result = crud.ingest_many(
        [
            _payload(url="https://elpais.com/ok-1"),
            _payload(url="https://elpais.com/boom-2"),
        ]
    )

    assert result.model_dump() == {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 2, "rolled_back": True}
    assert session.query(ArticleORM).count() == 0



def test_ingest_many_tracks_insert_update_and_unchanged_without_row_by_row_commits():
    session = _session()
    crud = ArticleCRUD(session)

    initial = crud.ingest_many([_payload(url="https://elpais.com/a"), _payload(url="https://elpais.com/b")])
    follow_up = crud.ingest_many([
        _payload(url="https://elpais.com/a", title="Title updated"),
        _payload(url="https://elpais.com/b"),
    ])

    assert initial.model_dump() == {"inserted": 2, "updated": 0, "unchanged": 0, "errors": 0, "rolled_back": False}
    assert follow_up.model_dump() == {"inserted": 0, "updated": 1, "unchanged": 1, "errors": 0, "rolled_back": False}
    rows = session.execute(select(ArticleORM).order_by(ArticleORM.url)).scalars().all()
    assert [row.title for row in rows] == ["Title updated", "Title"]
