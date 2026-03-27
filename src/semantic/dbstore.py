"""Stable facade for semantic storage and explorer helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.semantic.store.embeddings import (
    DEFAULT_NEIGHBOR_LIMIT,
    MIN_TEXT_LENGTH,
    NeighborRow,
    SeedArticleRow,
    SemanticCandidate,
    assemble_article_text,
    build_candidate,
    content_hash_for_text,
    load_embedding_artifacts,
    load_neighbors_for_articles,
    load_seed_article,
    nearest_neighbors,
    select_embedding_candidates,
    summary_snippet,
    upsert_embeddings,
)
from src.semantic.store.explorer import (
    ExplorerArticleDetailRecord,
    ExplorerFilters,
    ExplorerPointsPage,
)
from src.semantic.store.explorer import (
    load_explorer_article_detail as _load_explorer_article_detail,
)
from src.semantic.store.explorer import (
    load_explorer_filter_options as _load_explorer_filter_options,
)
from src.semantic.store.explorer import (
    load_explorer_points_page as _load_explorer_points_page,
)
from src.semantic.store.projections import (
    DEFAULT_PROJECTION_KIND,
    DEFAULT_PROJECTION_SET,
    DEFAULT_PROJECTION_VERSION,
    load_projected_points,
    projection_kind_for_set,
    refresh_projection_set,
)
from src.semantic.store.schema import (
    DEFAULT_EMBEDDING_MODEL,
    SemanticWindow,
    embedding_dimensions_for_model,
    ensure_vector_index,
    get_embedding_vector_dimensions,
    init_pgvector_schema,
    render_additive_schema_sql,
    render_init_sql,
    resolve_semantic_window,
)
from src.semantic.store.sql import parse_vector_text, vector_literal
from src.semantic.store.story_memberships import (
    load_story_cluster_memberships as _load_story_cluster_memberships,
)
from src.semantic.store.story_priority import (
    StoryClusterPriorityGroup,
    select_cluster_aware_article_ids,
    select_source_balanced_article_ids,
)
from src.semantic.store.story_priority import (
    load_story_cluster_priority_groups as _load_story_cluster_priority_groups,
)


def load_explorer_points_page(session: Session, *, filters: ExplorerFilters) -> ExplorerPointsPage:
    return _load_explorer_points_page(
        session,
        filters=filters,
        nearest_neighbors_fn=nearest_neighbors,
    )


def load_explorer_filter_options(session: Session, *, projection_set: str) -> dict:
    return _load_explorer_filter_options(session, projection_set=projection_set)


def load_explorer_article_detail(
    session: Session,
    *,
    article_id: int,
    projection_set: str,
) -> ExplorerArticleDetailRecord | None:
    return _load_explorer_article_detail(
        session,
        article_id=article_id,
        projection_set=projection_set,
        nearest_neighbors_fn=nearest_neighbors,
    )


__all__ = [
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_NEIGHBOR_LIMIT",
    "DEFAULT_PROJECTION_KIND",
    "DEFAULT_PROJECTION_SET",
    "DEFAULT_PROJECTION_VERSION",
    "ExplorerArticleDetailRecord",
    "ExplorerFilters",
    "ExplorerPointsPage",
    "MIN_TEXT_LENGTH",
    "NeighborRow",
    "SeedArticleRow",
    "SemanticCandidate",
    "SemanticWindow",
    "StoryClusterPriorityGroup",
    "_load_story_cluster_memberships",
    "_load_story_cluster_priority_groups",
    "assemble_article_text",
    "build_candidate",
    "content_hash_for_text",
    "embedding_dimensions_for_model",
    "ensure_vector_index",
    "get_embedding_vector_dimensions",
    "init_pgvector_schema",
    "load_embedding_artifacts",
    "load_explorer_article_detail",
    "load_explorer_filter_options",
    "load_explorer_points_page",
    "load_neighbors_for_articles",
    "load_projected_points",
    "load_seed_article",
    "nearest_neighbors",
    "parse_vector_text",
    "projection_kind_for_set",
    "refresh_projection_set",
    "render_additive_schema_sql",
    "render_init_sql",
    "resolve_semantic_window",
    "select_cluster_aware_article_ids",
    "select_embedding_candidates",
    "select_source_balanced_article_ids",
    "summary_snippet",
    "upsert_embeddings",
    "vector_literal",
]
