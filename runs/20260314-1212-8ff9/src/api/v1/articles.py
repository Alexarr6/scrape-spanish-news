from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.persistence.contracts import ArticleCreate, ArticleRead, IngestResult
from src.persistence.crud import ArticleCRUD

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])


def get_session() -> Session:
    # Runtime wiring intentionally minimal for v1; caller can override dependency in tests/app boot.
    raise RuntimeError("DB session dependency is not configured")


@router.get("", response_model=list[ArticleRead])
def list_articles(limit: int = 100, offset: int = 0, session: Session = Depends(get_session)) -> list[ArticleRead]:
    return ArticleCRUD(session).list(limit=limit, offset=offset)


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(article_id: int, session: Session = Depends(get_session)) -> ArticleRead:
    article = ArticleCRUD(session).get(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("", response_model=ArticleRead)
def upsert_article(payload: ArticleCreate, session: Session = Depends(get_session)) -> ArticleRead:
    article, _ = ArticleCRUD(session).upsert(payload)
    return article


@router.post("/ingest", response_model=IngestResult)
def ingest_articles(payload: list[ArticleCreate], session: Session = Depends(get_session)) -> IngestResult:
    return ArticleCRUD(session).ingest_many(payload)
