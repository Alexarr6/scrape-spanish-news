from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.analysis.readside import (
    ClusterListFilters,
    load_story_cluster_detail,
    load_story_cluster_filters,
    load_story_clusters,
)
from src.api.contracts.clusters import (
    StoryClusterDetail,
    StoryClusterFiltersResponse,
    StoryClusterListMeta,
    StoryClusterListResponse,
)
from src.api.v1.articles import get_session

router = APIRouter(prefix="/api/v1/clusters", tags=["story-clusters"])


@router.get("", response_model=StoryClusterListResponse)
def list_story_clusters(
    session: Session = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    source: str | None = None,
    tag_code: str | None = None,
    entity_slug: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
) -> StoryClusterListResponse:
    """List story clusters using filter params already shaped for the read-side."""

    items, total = load_story_clusters(
        session,
        ClusterListFilters(
            limit=limit,
            offset=offset,
            source=source,
            tag_code=tag_code,
            entity_slug=entity_slug,
            date_from=date_from,
            date_to=date_to,
            search=search,
        ),
    )
    return StoryClusterListResponse(items=items, meta=StoryClusterListMeta(total=total, limit=limit, offset=offset))


@router.get("/filters", response_model=StoryClusterFiltersResponse)
def get_story_cluster_filters(
    session: Session = Depends(get_session),
    source: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
) -> StoryClusterFiltersResponse:
    """Return source, tag, and entity filters for the currently matched cluster set."""

    payload = load_story_cluster_filters(
        session,
        ClusterListFilters(source=source, date_from=date_from, date_to=date_to, search=search),
    )
    return StoryClusterFiltersResponse(**payload)


@router.get("/{cluster_id}", response_model=StoryClusterDetail)
def get_story_cluster(cluster_id: int, session: Session = Depends(get_session)) -> StoryClusterDetail:
    """Return one story cluster detail payload or a 404 when the id is unknown."""

    payload = load_story_cluster_detail(session, cluster_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Story cluster not found")
    return StoryClusterDetail(**payload)
