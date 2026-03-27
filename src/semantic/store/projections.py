from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.semantic.analyze import analyze_points
from src.semantic.contracts import EmbeddingArtifact, PointArtifact
from src.semantic.explorer_readside import analysis_for_row, editorial_preview_for_row
from src.semantic.project import project_embeddings
from src.semantic.store.embeddings import (
    DEFAULT_NEIGHBOR_LIMIT,
    load_embedding_artifacts,
    load_neighbors_for_articles,
)
from src.semantic.store.schema import SemanticWindow, apply_article_date_window
from src.semantic.store.sql import utc_now

DEFAULT_PROJECTION_KIND = "pca_3d"
DEFAULT_PROJECTION_SET = "pca_3d_latest"
DEFAULT_PROJECTION_VERSION = "v1"


def projection_kind_for_set(projection_set: str) -> str:
    if projection_set.startswith("pca_2d"):
        return "pca_2d"
    if projection_set.startswith("pca_3d"):
        return "pca_3d"
    return DEFAULT_PROJECTION_KIND


def refresh_projection_set(
    session: Session,
    *,
    projection_set: str,
    projection_version: str = DEFAULT_PROJECTION_VERSION,
    window: SemanticWindow | None = None,
) -> int:
    projection_kind = projection_kind_for_set(projection_set)
    embeddings = load_embedding_artifacts(session, window=window)
    points = project_embeddings(
        embeddings,
        dimensions=3 if projection_kind == "pca_3d" else 2,
    )
    now = utc_now()
    session.execute(
        text("DELETE FROM article_projections WHERE projection_set = :projection_set"),
        {"projection_set": projection_set},
    )
    session.execute(
        text("DELETE FROM semantic_point_analysis WHERE projection_set = :projection_set"),
        {"projection_set": projection_set},
    )
    session.execute(
        text("DELETE FROM semantic_clusters WHERE projection_set = :projection_set"),
        {"projection_set": projection_set},
    )
    for point in points:
        embedding_id = session.execute(
            text("SELECT id FROM article_embeddings WHERE article_id = :article_id"),
            {"article_id": point.article_id},
        ).scalar_one()
        session.execute(
            text(
                """
                INSERT INTO article_projections (
                  article_id, embedding_id, projection_set, projection_kind, projection_version,
                  x, y, z, projected_at, updated_at
                ) VALUES (
                  :article_id, :embedding_id, :projection_set,
                  :projection_kind, :projection_version,
                  :x, :y, :z, :projected_at, :updated_at
                )
                ON CONFLICT (article_id, projection_set) DO UPDATE SET
                  embedding_id = EXCLUDED.embedding_id,
                  projection_kind = EXCLUDED.projection_kind,
                  projection_version = EXCLUDED.projection_version,
                  x = EXCLUDED.x,
                  y = EXCLUDED.y,
                  z = EXCLUDED.z,
                  projected_at = EXCLUDED.projected_at,
                  updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "article_id": point.article_id,
                "embedding_id": embedding_id,
                "projection_set": projection_set,
                "projection_kind": projection_kind,
                "projection_version": projection_version,
                "x": point.x,
                "y": point.y,
                "z": point.z,
                "projected_at": now,
                "updated_at": now,
            },
        )
    _persist_projection_analysis(
        session, projection_set=projection_set, points=points, embeddings=embeddings
    )
    session.commit()
    return len(points)


def load_projected_points(
    session: Session,
    *,
    projection_set: str,
    include_neighbors: bool = False,
    neighbor_limit: int = DEFAULT_NEIGHBOR_LIMIT,
    window: SemanticWindow | None = None,
) -> list[PointArtifact]:
    projection_kind = projection_kind_for_set(projection_set)
    sql = """
            SELECT a.id AS article_id, a.source, a.title, a.url,
                   COALESCE(
                     to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SSOF'),
                     ''
                   ) AS published_at,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '')
                     AS published_date,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '')
                     AS display_date,
                   a.section, e.summary_snippet, e.source_text_chars, e.embedding_model,
                   p.x, p.y, COALESCE(p.z, 0.0) AS z,
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
            JOIN article_embeddings e ON e.id = p.embedding_id
            JOIN articles a ON a.id = p.article_id
            LEFT JOIN semantic_point_analysis spa
              ON spa.article_id = p.article_id
             AND spa.projection_set = p.projection_set
            LEFT JOIN article_editorial_analysis aea
              ON aea.article_id = p.article_id
    """
    params = {"projection_set": projection_set, "projection_kind": projection_kind}
    clauses = [
        "p.projection_set = :projection_set",
        "p.projection_kind = :projection_kind",
    ]
    apply_article_date_window(clauses, params, window=window)
    sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY a.published_at DESC NULLS LAST, a.id DESC"
    rows = session.execute(text(sql), params).mappings().all()
    points = [
        PointArtifact(
            article_id=row["article_id"],
            source=row["source"],
            title=row["title"],
            url=row["url"],
            published_at=row["published_at"] or "",
            published_date=row["published_date"] or "",
            display_date=row["display_date"] or (row["published_at"] or "")[:10],
            section=row["section"] or "",
            summary_snippet=row["summary_snippet"] or "",
            text_length=row["source_text_chars"] or 0,
            embedding_model=row["embedding_model"],
            x=float(row["x"]),
            y=float(row["y"]),
            z=float(row["z"]),
            editorial_preview=editorial_preview_for_row(row),
            analysis=analysis_for_row(row, neighbors=[]),
        )
        for row in rows
    ]
    if include_neighbors and points:
        neighbor_map = load_neighbors_for_articles(
            session,
            article_ids=[point.article_id for point in points],
            limit=neighbor_limit,
        )
        for point in points:
            point.neighbors = neighbor_map.get(point.article_id, [])
    return points


def _persist_projection_analysis(
    session: Session,
    *,
    projection_set: str,
    points: list[PointArtifact],
    embeddings: list[EmbeddingArtifact],
) -> None:
    analysis = analyze_points(points, embeddings)
    analysis_by_id = {point.article_id: point for point in analysis.points}
    now = utc_now()
    session.execute(
        text("DELETE FROM semantic_point_analysis WHERE projection_set = :projection_set"),
        {"projection_set": projection_set},
    )
    session.execute(
        text("DELETE FROM semantic_clusters WHERE projection_set = :projection_set"),
        {"projection_set": projection_set},
    )
    for point in points:
        point.analysis = analysis_by_id.get(point.article_id, point.analysis)
        session.execute(
            text(
                """
                INSERT INTO semantic_point_analysis (
                  article_id, projection_set, cluster_id, cluster_size, is_outlier,
                  local_density_distance, source_neighbor_diversity, nearby_sources_json, updated_at
                ) VALUES (
                  :article_id, :projection_set, :cluster_id, :cluster_size, :is_outlier,
                  :local_density_distance, :source_neighbor_diversity, :nearby_sources_json, :updated_at
                )
                """
            ),
            {
                "article_id": point.article_id,
                "projection_set": projection_set,
                "cluster_id": point.analysis.cluster_id,
                "cluster_size": point.analysis.cluster_size,
                "is_outlier": point.analysis.is_outlier,
                "local_density_distance": point.analysis.local_density_distance,
                "source_neighbor_diversity": point.analysis.source_neighbor_diversity,
                "nearby_sources_json": json.dumps(point.analysis.nearby_sources),
                "updated_at": now,
            },
        )
    for cluster in analysis.clusters:
        session.execute(
            text(
                """
                INSERT INTO semantic_clusters (
                  projection_set, cluster_id, size, article_ids_json, representative_article_ids_json,
                  top_sources_json, source_count, source_dominance, date_min, date_max,
                  centroid_x, centroid_y, centroid_z, updated_at
                ) VALUES (
                  :projection_set, :cluster_id, :size, :article_ids_json, :representative_article_ids_json,
                  :top_sources_json, :source_count, :source_dominance, :date_min, :date_max,
                  :centroid_x, :centroid_y, :centroid_z, :updated_at
                )
                """
            ),
            {
                "projection_set": projection_set,
                "cluster_id": cluster.cluster_id,
                "size": cluster.size,
                "article_ids_json": json.dumps(cluster.article_ids),
                "representative_article_ids_json": json.dumps(cluster.representative_article_ids),
                "top_sources_json": json.dumps(cluster.top_sources),
                "source_count": cluster.source_count,
                "source_dominance": cluster.source_dominance,
                "date_min": cluster.date_min,
                "date_max": cluster.date_max,
                "centroid_x": cluster.centroid_x,
                "centroid_y": cluster.centroid_y,
                "centroid_z": cluster.centroid_z,
                "updated_at": now,
            },
        )

