from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.analysis.readside import (
    EditorialAnalysisListFilters,
    load_article_editorial_analysis,
    load_article_editorial_analysis_list,
)
from src.api.contracts.editorial import (
    ArticleEditorialAnalysisListResponse,
    ArticleEditorialAnalysisResponse,
)
from src.api.v1.articles import get_session

router = APIRouter(prefix="/api/v1/editorial-analysis", tags=["editorial-analysis"])


@router.get("", response_model=ArticleEditorialAnalysisListResponse)
def list_editorial_analysis(
    source: str | None = None,
    bias_label: str | None = None,
    article_type: str | None = None,
    analysis_status: str | None = Query(default=None, alias="status"),
    tone_emotional: str | None = None,
    opinionatedness: str | None = None,
    min_bias_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="published_at_desc"),
    session: Session = Depends(get_session),
) -> ArticleEditorialAnalysisListResponse:
    filters = EditorialAnalysisListFilters(
        source=source,
        bias_label=bias_label,
        article_type=article_type,
        analysis_status=analysis_status,
        tone_emotional=tone_emotional,
        opinionatedness=opinionatedness,
        min_bias_confidence=min_bias_confidence,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        sort=sort,
    )
    items, total = load_article_editorial_analysis_list(session, filters)
    return ArticleEditorialAnalysisListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get("/{article_id}", response_model=ArticleEditorialAnalysisResponse)
def get_article_editorial_analysis(
    article_id: int,
    session: Session = Depends(get_session),
) -> ArticleEditorialAnalysisResponse:
    payload = load_article_editorial_analysis(session, article_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Editorial analysis not found")
    return ArticleEditorialAnalysisResponse.model_validate(payload)
