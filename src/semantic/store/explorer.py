from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.semantic.contracts import NeighborArtifact, PointArtifact
from src.semantic.explorer_readside import (
    analysis_for_row,
    editorial_preview_for_row,
    load_available_clusters,
    load_cluster_summaries,
    load_distinct_values,
    load_explorer_editorial_metadata,
    load_filtered_distinct_values,
    load_projection_bounds,
)
from src.semantic.store.embeddings import NeighborRow
from src.semantic.store.projections import DEFAULT_PROJECTION_SET, projection_kind_for_set
from src.semantic.store.sql import explorer_published_at_sql, session_dialect_name
from src.semantic.store.story_memberships import load_story_cluster_memberships


@dataclass
class ExplorerFilters:
    projection_set: str = DEFAULT_PROJECTION_SET
    limit: int = 250
    source: str | None = None
    section: str | None = None
    cluster_id: int | None = None
    story_cluster_id: int | None = None
    visual_mode: str | None = None
    editorial_dimension: str | None = None
    editorial_value: str | None = None
    outlier_only: bool = False
    date_from: str | None = None
    date_to: str | None = None
    search: str | None = None


@dataclass
class ExplorerPointsPage:
    items: list[PointArtifact]
    total: int
    limit: int
    projection_set: str
    bounds: dict[str, float] | None
    available_sources: list[str]
    available_sections: list[str]
    available_clusters: list[int]
    cluster_summaries: list[dict[str, Any]]
    story_cluster_metadata_available: bool = False
    editorial: dict[str, Any] | None = None


@dataclass
class ExplorerArticleDetailRecord:
    article: dict[str, Any]
    projection_set: str
    point: PointArtifact | None
    neighbors: list[NeighborArtifact]


def load_explorer_points_page(
    session: Session,
    *,
    filters: ExplorerFilters,
    nearest_neighbors_fn: Callable[[Session], list[NeighborRow]] | Any,
) -> ExplorerPointsPage:
    projection_kind = projection_kind_for_set(filters.projection_set)
    where_sql, params = _build_explorer_where_clause(filters, projection_kind=projection_kind)
    published_at_sql = explorer_published_at_sql(dialect_name=session_dialect_name(session))
    visual_mode = (filters.visual_mode or "filter").lower()
    order_by_sql = "ORDER BY a.published_at DESC, a.id DESC"
    if filters.story_cluster_id is not None and visual_mode == "highlight":
        order_by_sql = """
            ORDER BY CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM cluster_members cm
                    WHERE cm.article_id = p.article_id
                      AND cm.cluster_id = :story_cluster_id
                ) THEN 0
                ELSE 1
            END,
            a.published_at DESC,
            a.id DESC
        """
    rows = (
        session.execute(
            text(
                f"""
            SELECT a.id AS article_id,
                   a.source,
                   a.title,
                   a.url,
                   {published_at_sql},
                   COALESCE(a.section, '') AS section,
                   COALESCE(e.summary_snippet, '') AS summary_snippet,
                   p.x,
                   p.y,
                   COALESCE(p.z, 0.0) AS z,
                   spa.cluster_id,
                   COALESCE(spa.cluster_size, 0) AS cluster_size,
                   COALESCE(spa.is_outlier, false) AS is_outlier,
                   COALESCE(spa.local_density_distance, 0.0) AS local_density_distance,
                   COALESCE(spa.source_neighbor_diversity, 0) AS source_neighbor_diversity,
                   COALESCE(spa.nearby_sources_json, '[]') AS nearby_sources_json,
                   aea.analysis_status AS editorial_analysis_status,
                   aea.editorial_applicability AS editorial_applicability,
                   aea.article_type AS editorial_article_type,
                   aea.article_type_confidence AS editorial_article_type_confidence,
                   aea.bias_label AS editorial_bias_label,
                   aea.bias_confidence AS editorial_bias_confidence,
                   aea.tone_emotional AS editorial_tone_emotional,
                   aea.unclear_reasons_json AS editorial_unclear_reasons_json,
                   aea.evidence_spans_json AS editorial_evidence_spans_json
            FROM article_projections p
            JOIN articles a ON a.id = p.article_id
            JOIN article_embeddings e ON e.id = p.embedding_id
            LEFT JOIN semantic_point_analysis spa
              ON spa.article_id = p.article_id
             AND spa.projection_set = p.projection_set
            LEFT JOIN article_editorial_analysis aea
              ON aea.article_id = p.article_id
            {where_sql}
            {order_by_sql}
            LIMIT :limit
            """
            ),
            {**params, "limit": filters.limit},
        )
        .mappings()
        .all()
    )
    story_cluster_ids_by_article = load_story_cluster_memberships(
        session,
        article_ids=[int(row["article_id"]) for row in rows],
    )
    items: list[PointArtifact] = []
    for row in rows:
        neighbors = _safe_neighbors(
            session,
            article_id=row["article_id"],
            limit=3,
            nearest_neighbors_fn=nearest_neighbors_fn,
        )
        items.append(
            PointArtifact(
                article_id=row["article_id"],
                source=row["source"] or "",
                title=row["title"] or "",
                url=row["url"] or "",
                published_at=str(row["published_at"] or ""),
                published_date=str(row["published_date"] or ""),
                display_date=str(row["display_date"] or ""),
                section=row["section"] or "",
                summary_snippet=row["summary_snippet"] or "",
                x=float(row["x"]),
                y=float(row["y"]),
                z=float(row["z"]),
                editorial_preview=editorial_preview_for_row(row),
                analysis=analysis_for_row(
                    row,
                    neighbors=neighbors,
                    story_cluster_ids=story_cluster_ids_by_article.get(int(row["article_id"]), []),
                ),
            )
        )
    total = session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM article_projections p
            JOIN articles a ON a.id = p.article_id
            JOIN article_embeddings e ON e.id = p.embedding_id
            LEFT JOIN semantic_point_analysis spa
              ON spa.article_id = p.article_id
             AND spa.projection_set = p.projection_set
            LEFT JOIN article_editorial_analysis aea
              ON aea.article_id = p.article_id
            {where_sql}
            """
        ),
        params,
    ).scalar_one()
    return ExplorerPointsPage(
        items=items,
        total=int(total),
        limit=filters.limit,
        projection_set=filters.projection_set,
        bounds=load_projection_bounds(
            session,
            projection_set=filters.projection_set,
            projection_kind_for_set=projection_kind_for_set,
        ),
        available_sources=load_filtered_distinct_values(
            session,
            column="a.source",
            where_sql=where_sql,
            params=params,
        ),
        available_sections=load_filtered_distinct_values(
            session,
            column="a.section",
            where_sql=where_sql,
            params=params,
        ),
        available_clusters=load_available_clusters(session, projection_set=filters.projection_set),
        cluster_summaries=load_cluster_summaries(session, projection_set=filters.projection_set),
        story_cluster_metadata_available=(
            filters.story_cluster_id is not None and visual_mode == "highlight"
        ),
        editorial=load_explorer_editorial_metadata(
            session,
            filters=filters,
            projection_kind_for_set=projection_kind_for_set,
            build_explorer_where_clause=_build_explorer_where_clause,
        ),
    )


def load_explorer_filter_options(session: Session, *, projection_set: str) -> dict[str, Any]:
    return {
        "projection_set": projection_set,
        "available_sources": load_distinct_values(
            session,
            column="a.source",
            projection_set=projection_set,
            projection_kind_for_set=projection_kind_for_set,
        ),
        "available_sections": load_distinct_values(
            session,
            column="a.section",
            projection_set=projection_set,
            projection_kind_for_set=projection_kind_for_set,
        ),
        "available_clusters": load_available_clusters(session, projection_set=projection_set),
        "cluster_summaries": load_cluster_summaries(session, projection_set=projection_set),
        "editorial": load_explorer_editorial_metadata(
            session,
            filters=ExplorerFilters(projection_set=projection_set),
            projection_kind_for_set=projection_kind_for_set,
            build_explorer_where_clause=_build_explorer_where_clause,
        ),
    }


def load_explorer_article_detail(
    session: Session,
    *,
    article_id: int,
    projection_set: str,
    nearest_neighbors_fn: Callable[[Session], list[NeighborRow]] | Any,
) -> ExplorerArticleDetailRecord | None:
    projection_kind = projection_kind_for_set(projection_set)
    published_at_sql = explorer_published_at_sql(dialect_name=session_dialect_name(session))
    row = (
        session.execute(
            text(
                f"""
            SELECT a.id AS article_id,
                   a.source,
                   a.title,
                   a.url,
                   {published_at_sql},
                   COALESCE(a.section, '') AS section,
                   COALESCE(a.summary, '') AS summary,
                   COALESCE(a.article_text, '') AS article_text,
                   p.x,
                   p.y,
                   COALESCE(p.z, 0.0) AS z,
                   COALESCE(e.summary_snippet, '') AS summary_snippet,
                   spa.cluster_id,
                   COALESCE(spa.cluster_size, 0) AS cluster_size,
                   COALESCE(spa.is_outlier, false) AS is_outlier,
                   COALESCE(spa.local_density_distance, 0.0) AS local_density_distance,
                   COALESCE(spa.source_neighbor_diversity, 0) AS source_neighbor_diversity,
                   COALESCE(spa.nearby_sources_json, '[]') AS nearby_sources_json,
                   aea.analysis_status AS editorial_analysis_status,
                   aea.editorial_applicability AS editorial_applicability,
                   aea.article_type AS editorial_article_type,
                   aea.article_type_confidence AS editorial_article_type_confidence,
                   aea.bias_label AS editorial_bias_label,
                   aea.bias_confidence AS editorial_bias_confidence,
                   aea.tone_emotional AS editorial_tone_emotional,
                   aea.unclear_reasons_json AS editorial_unclear_reasons_json,
                   aea.evidence_spans_json AS editorial_evidence_spans_json
            FROM articles a
            LEFT JOIN article_embeddings e ON e.article_id = a.id
            LEFT JOIN article_projections p
              ON p.article_id = a.id
             AND p.projection_set = :projection_set
             AND p.projection_kind = :projection_kind
            LEFT JOIN semantic_point_analysis spa
              ON spa.article_id = a.id
             AND spa.projection_set = :projection_set
            LEFT JOIN article_editorial_analysis aea
              ON aea.article_id = a.id
            WHERE a.id = :article_id
            """
            ),
            {
                "article_id": article_id,
                "projection_set": projection_set,
                "projection_kind": projection_kind,
            },
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    neighbors = _safe_neighbors(
        session,
        article_id=article_id,
        limit=5,
        nearest_neighbors_fn=nearest_neighbors_fn,
    )
    story_cluster_ids_by_article = load_story_cluster_memberships(session, article_ids=[article_id])
    point = None
    if row["x"] is not None and row["y"] is not None:
        point = PointArtifact(
            article_id=row["article_id"],
            source=row["source"] or "",
            title=row["title"] or "",
            url=row["url"] or "",
            published_at=str(row["published_at"] or ""),
            published_date=str(row["published_date"] or ""),
            display_date=str(row["display_date"] or ""),
            section=row["section"] or "",
            summary_snippet=row["summary_snippet"] or "",
            x=float(row["x"]),
            y=float(row["y"]),
            z=float(row["z"]),
            editorial_preview=editorial_preview_for_row(row),
            analysis=analysis_for_row(
                row,
                neighbors=neighbors,
                story_cluster_ids=story_cluster_ids_by_article.get(article_id, []),
            ),
        )
    return ExplorerArticleDetailRecord(
        article={
            "article_id": row["article_id"],
            "source": row["source"] or "",
            "title": row["title"] or "",
            "url": row["url"] or "",
            "published_at": str(row["published_at"] or ""),
            "published_date": str(row["published_date"] or ""),
            "display_date": str(row["display_date"] or ""),
            "section": row["section"] or "",
            "summary": row["summary"] or "",
            "article_text_excerpt": (row["article_text"] or "")[:400],
        },
        projection_set=projection_set,
        point=point,
        neighbors=neighbors,
    )


def _build_explorer_where_clause(
    filters: ExplorerFilters, *, projection_kind: str | None = None
) -> tuple[str, dict[str, Any]]:
    resolved_projection_kind = projection_kind or projection_kind_for_set(filters.projection_set)
    clauses = ["p.projection_set = :projection_set", "p.projection_kind = :projection_kind"]
    params: dict[str, Any] = {
        "projection_set": filters.projection_set,
        "projection_kind": resolved_projection_kind,
    }
    if filters.source:
        clauses.append("a.source = :source")
        params["source"] = filters.source
    if filters.section:
        clauses.append("a.section = :section")
        params["section"] = filters.section
    if filters.date_from:
        clauses.append("date(a.published_at) >= date(:date_from)")
        params["date_from"] = filters.date_from
    if filters.date_to:
        clauses.append("date(a.published_at) <= date(:date_to)")
        params["date_to"] = filters.date_to
    visual_mode = (filters.visual_mode or "filter").lower()
    if filters.search:
        params["search"] = f"%{filters.search.strip().lower()}%"
        if visual_mode == "filter":
            clauses.append("(lower(a.title) LIKE :search OR lower(a.summary) LIKE :search)")
    if filters.story_cluster_id is not None:
        params["story_cluster_id"] = filters.story_cluster_id
        if visual_mode == "filter":
            clauses.append(
                "EXISTS (SELECT 1 FROM cluster_members cm WHERE cm.article_id = p.article_id AND cm.cluster_id = :story_cluster_id)"
            )
    if filters.editorial_dimension and filters.editorial_value:
        params["editorial_value"] = filters.editorial_value
        if filters.editorial_dimension == "article_type" and visual_mode == "filter":
            clauses.append("aea.article_type = :editorial_value")
        elif filters.editorial_dimension == "bias_label" and visual_mode == "filter":
            clauses.extend(
                [
                    "COALESCE(aea.analysis_status, 'pending') = 'completed'",
                    "COALESCE(aea.editorial_applicability, 'full') = 'full'",
                    "COALESCE(aea.bias_label, 'unclear') = :editorial_value",
                    "COALESCE(aea.bias_label, 'unclear') <> 'unclear'",
                    "COALESCE(aea.bias_confidence, 0.0) >= 0.45",
                ]
            )
    if filters.cluster_id is not None or filters.outlier_only:
        clauses.append("spa.projection_set = :analysis_projection_set")
        params["analysis_projection_set"] = filters.projection_set
    if filters.cluster_id is not None:
        clauses.append("spa.cluster_id = :cluster_id")
        params["cluster_id"] = filters.cluster_id
    if filters.outlier_only:
        clauses.append("spa.is_outlier = :outlier_only")
        params["outlier_only"] = True
    return "WHERE " + " AND ".join(clauses), params


def _safe_neighbors(
    session: Session,
    *,
    article_id: int,
    limit: int,
    nearest_neighbors_fn: Callable[[Session], list[NeighborRow]] | Any,
) -> list[NeighborArtifact]:
    try:
        return [
            row.to_artifact()
            for row in nearest_neighbors_fn(session, article_id=article_id, limit=limit)
        ]
    except Exception:
        return []
