from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.analysis.readside import load_article_editorial_analysis
from src.api.contracts.editorial import ArticleEditorialAnalysisResponse
from src.api.v1.articles import get_session

router = APIRouter(prefix="/api/v1/editorial-analysis", tags=["editorial-analysis"])


@router.get("/{article_id}", response_model=ArticleEditorialAnalysisResponse)
def get_article_editorial_analysis(
    article_id: int,
    session: Session = Depends(get_session),
) -> ArticleEditorialAnalysisResponse:
    payload = load_article_editorial_analysis(session, article_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Editorial analysis not found")
    return ArticleEditorialAnalysisResponse.model_validate(payload)
