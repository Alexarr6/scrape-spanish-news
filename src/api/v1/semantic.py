from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.analysis.readside import load_article_editorial_summary
from src.api.contracts.semantic import (
    ExplorerArticleDetail,
    ExplorerFiltersResponse,
    ExplorerMeta,
    ExplorerNeighbor,
    ExplorerPoint,
    ExplorerPointsResponse,
    ExplorerProjectionBounds,
    ExplorerSemanticSummary,
)
from src.api.v1.articles import get_session
from src.semantic.dbstore import (
    DEFAULT_PROJECTION_SET,
    ExplorerArticleDetailRecord,
    ExplorerFilters,
    ExplorerPointsPage,
    load_explorer_article_detail,
    load_explorer_filter_options,
    load_explorer_points_page,
)

router = APIRouter(prefix="/api/v1/semantic/explorer", tags=["semantic-explorer"])


@router.get("/points", response_model=ExplorerPointsResponse)
def get_explorer_points(
    session: Session = Depends(get_session),
    projection_set: str = DEFAULT_PROJECTION_SET,
    limit: Annotated[int, Query(ge=1, le=500)] = 250,
    source: str | None = None,
    section: str | None = None,
    cluster_id: int | None = None,
    story_cluster_id: int | None = Query(default=None, alias="sem_story_cluster"),
    outlier_only: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
) -> ExplorerPointsResponse:
    """Return explorer points plus the metadata needed to drive the UI shell."""

    filters = ExplorerFilters(
        projection_set=projection_set,
        limit=limit,
        source=source,
        section=section,
        cluster_id=cluster_id,
        story_cluster_id=story_cluster_id,
        outlier_only=outlier_only,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    page = load_explorer_points_page(session, filters=filters)
    return _to_points_response(page)


@router.get("/filters", response_model=ExplorerFiltersResponse)
def get_explorer_filters(
    session: Session = Depends(get_session),
    projection_set: str = DEFAULT_PROJECTION_SET,
) -> ExplorerFiltersResponse:
    """Return semantic explorer filter options for one projection set."""

    options = load_explorer_filter_options(session, projection_set=projection_set)
    return ExplorerFiltersResponse(**options)


@router.get("/articles/{article_id}", response_model=ExplorerArticleDetail)
def get_explorer_article_detail(
    article_id: int,
    session: Session = Depends(get_session),
    projection_set: str = DEFAULT_PROJECTION_SET,
) -> ExplorerArticleDetail:
    """Return one explorer article detail payload with neighbors and semantic summary."""

    detail = load_explorer_article_detail(
        session,
        article_id=article_id,
        projection_set=projection_set,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Semantic explorer article not found")
    editorial = load_article_editorial_summary(session, article_id=article_id)
    return _to_article_detail_response(detail, editorial=editorial)


def _to_points_response(page: ExplorerPointsPage) -> ExplorerPointsResponse:
    """Translate the DB/read-side page object into the API response contract."""

    bounds = None
    if page.bounds is not None:
        bounds = ExplorerProjectionBounds(**page.bounds)
    return ExplorerPointsResponse(
        items=[_to_point_model(item) for item in page.items],
        meta=ExplorerMeta(
            total=page.total,
            returned=len(page.items),
            limit=page.limit,
            projection_set=page.projection_set,
            bounds=bounds,
            available_sources=page.available_sources,
            available_sections=page.available_sections,
            available_clusters=page.available_clusters,
            cluster_summaries=page.cluster_summaries,
        ),
    )


def _to_article_detail_response(
    detail: ExplorerArticleDetailRecord, *, editorial: dict | None = None
) -> ExplorerArticleDetail:
    point_model = (
        _to_point_model(detail.point, neighbor_count=len(detail.neighbors))
        if detail.point is not None
        else None
    )
    semantic_summary = (
        point_model.analysis if point_model is not None else ExplorerSemanticSummary()
    )
    return ExplorerArticleDetail(
        article=detail.article,
        projection_set=detail.projection_set,
        point=point_model,
        semantic_summary=semantic_summary,
        editorial=editorial,
        neighbors=[ExplorerNeighbor(**neighbor.model_dump()) for neighbor in detail.neighbors],
    )


def _to_point_model(item, *, neighbor_count: int = 0) -> ExplorerPoint:
    payload = item.model_dump()
    analysis = payload.pop("analysis", {}) or {}
    analysis.setdefault("neighbor_count", neighbor_count)
    return ExplorerPoint(**payload, analysis=ExplorerSemanticSummary(**analysis))
