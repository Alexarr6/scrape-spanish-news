"""Explorer read-model shaping helpers extracted from semantic dbstore."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.semantic.contracts import NeighborArtifact, PointAnalysisArtifact


def editorial_preview_for_row(row: Any) -> dict[str, Any]:
    analysis_status = str(row.get("editorial_analysis_status") or "pending")
    editorial_applicability = str(row.get("editorial_applicability") or "full")
    article_type = str(row.get("editorial_article_type") or "unclear")
    article_type_confidence = float(row.get("editorial_article_type_confidence") or 0.0)
    bias_label = str(row.get("editorial_bias_label") or "unclear")
    bias_confidence = float(row.get("editorial_bias_confidence") or 0.0)
    unclear_reasons = parse_json_scalar_list(row.get("editorial_unclear_reasons_json"))
    evidence_spans = parse_json_list(row.get("editorial_evidence_spans_json"))
    return {
        "analysis_status": analysis_status,
        "editorial_applicability": editorial_applicability,
        "article_type": article_type,
        "article_type_confidence": article_type_confidence,
        "bias_label": bias_label,
        "bias_confidence": bias_confidence,
        "review_flags": build_editorial_review_flags(
            analysis_status=analysis_status,
            bias_label=bias_label,
            bias_confidence=bias_confidence,
            evidence_spans=evidence_spans,
            unclear_reasons=unclear_reasons,
            editorial_applicability=editorial_applicability,
        ),
    }


def analysis_for_row(
    row: Any,
    *,
    neighbors: list[NeighborArtifact],
    story_cluster_ids: list[int] | None = None,
) -> PointAnalysisArtifact:
    return PointAnalysisArtifact(
        article_id=row["article_id"],
        cluster_id=row.get("cluster_id"),
        cluster_size=int(row.get("cluster_size") or 0),
        is_outlier=bool(row.get("is_outlier")),
        local_density_distance=float(row.get("local_density_distance") or 0.0),
        source_neighbor_diversity=int(
            row.get("source_neighbor_diversity") or len({neighbor.source for neighbor in neighbors})
        ),
        nearby_sources=sorted(
            set(json.loads(row.get("nearby_sources_json") or "[]") or [])
            | {neighbor.source for neighbor in neighbors}
        ),
        story_cluster_ids=sorted(set(story_cluster_ids or [])),
    )


def load_explorer_editorial_metadata(
    session: Session,
    *,
    filters: Any,
    projection_kind_for_set: Any,
    build_explorer_where_clause: Any,
) -> dict[str, Any]:
    projection_kind = projection_kind_for_set(filters.projection_set)
    where_sql, params = build_explorer_where_clause(filters, projection_kind=projection_kind)
    article_type_rows = (
        session.execute(
            text(
                f"""
                SELECT COALESCE(aea.article_type, 'unclear') AS value, COUNT(*) AS count
                FROM article_projections p
                JOIN articles a ON a.id = p.article_id
                JOIN article_embeddings e ON e.id = p.embedding_id
                LEFT JOIN semantic_point_analysis spa
                  ON spa.article_id = p.article_id
                 AND spa.projection_set = p.projection_set
                LEFT JOIN article_editorial_analysis aea
                  ON aea.article_id = p.article_id
                {where_sql}
                GROUP BY COALESCE(aea.article_type, 'unclear')
                ORDER BY count DESC, value ASC
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    bias_rows = (
        session.execute(
            text(
                f"""
                SELECT COALESCE(aea.bias_label, 'unclear') AS value, COUNT(*) AS count
                FROM article_projections p
                JOIN articles a ON a.id = p.article_id
                JOIN article_embeddings e ON e.id = p.embedding_id
                LEFT JOIN semantic_point_analysis spa
                  ON spa.article_id = p.article_id
                 AND spa.projection_set = p.projection_set
                LEFT JOIN article_editorial_analysis aea
                  ON aea.article_id = p.article_id
                {where_sql}
                  AND COALESCE(aea.analysis_status, 'pending') = 'completed'
                  AND COALESCE(aea.editorial_applicability, 'full') = 'full'
                  AND COALESCE(aea.bias_label, 'unclear') <> 'unclear'
                  AND COALESCE(aea.bias_confidence, 0.0) >= 0.45
                GROUP BY COALESCE(aea.bias_label, 'unclear')
                ORDER BY count DESC, value ASC
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    coverage_row = (
        session.execute(
            text(
                f"""
                SELECT
                  COUNT(*) AS total,
                  SUM(CASE WHEN aea.article_id IS NULL OR COALESCE(aea.analysis_status, 'pending') = 'pending' THEN 1 ELSE 0 END) AS pending,
                  SUM(CASE WHEN COALESCE(aea.analysis_status, '') = 'failed' THEN 1 ELSE 0 END) AS failed,
                  SUM(CASE WHEN COALESCE(aea.article_type, 'unclear') = 'unclear' THEN 1 ELSE 0 END) AS unknown,
                  SUM(CASE WHEN COALESCE(aea.editorial_applicability, 'full') = 'limited' THEN 1 ELSE 0 END) AS limited,
                  SUM(CASE WHEN COALESCE(aea.editorial_applicability, 'full') = 'out_of_domain' THEN 1 ELSE 0 END) AS out_of_domain,
                  SUM(CASE WHEN COALESCE(aea.analysis_status, 'pending') = 'completed' THEN 1 ELSE 0 END) AS bias_total_completed,
                  SUM(CASE WHEN COALESCE(aea.analysis_status, 'pending') = 'completed' AND COALESCE(aea.bias_confidence, 0.0) < 0.45 THEN 1 ELSE 0 END) AS bias_low_confidence,
                  SUM(CASE WHEN COALESCE(aea.analysis_status, 'pending') = 'completed' AND COALESCE(aea.bias_label, 'unclear') = 'unclear' THEN 1 ELSE 0 END) AS bias_unknown,
                  SUM(CASE WHEN aea.article_id IS NULL OR COALESCE(aea.analysis_status, 'pending') = 'pending' THEN 1 ELSE 0 END) AS bias_pending,
                  SUM(CASE WHEN COALESCE(aea.analysis_status, '') = 'failed' THEN 1 ELSE 0 END) AS bias_failed,
                  SUM(CASE WHEN COALESCE(aea.editorial_applicability, 'full') = 'limited' THEN 1 ELSE 0 END) AS bias_limited,
                  SUM(CASE WHEN COALESCE(aea.editorial_applicability, 'full') = 'out_of_domain' THEN 1 ELSE 0 END) AS bias_out_of_domain
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
        )
        .mappings()
        .first()
    )
    coverage = coverage_row or {}
    return {
        "article_type": [
            {"value": str(row["value"]), "count": int(row["count"] or 0)}
            for row in article_type_rows
            if row["value"]
        ],
        "bias_label": [
            {"value": str(row["value"]), "count": int(row["count"] or 0)}
            for row in bias_rows
            if row["value"]
        ],
        "coverage": {
            key: int(coverage.get(key) or 0)
            for key in [
                "total",
                "pending",
                "failed",
                "unknown",
                "limited",
                "out_of_domain",
                "bias_total_completed",
                "bias_low_confidence",
                "bias_unknown",
                "bias_pending",
                "bias_failed",
                "bias_limited",
                "bias_out_of_domain",
            ]
        },
    }


def load_projection_bounds(
    session: Session,
    *,
    projection_set: str,
    projection_kind_for_set: Any,
) -> dict[str, float] | None:
    projection_kind = projection_kind_for_set(projection_set)
    row = (
        session.execute(
            text(
                """
            SELECT MIN(x) AS min_x,
                   MAX(x) AS max_x,
                   MIN(y) AS min_y,
                   MAX(y) AS max_y,
                   MIN(COALESCE(z, 0.0)) AS min_z,
                   MAX(COALESCE(z, 0.0)) AS max_z
            FROM article_projections
            WHERE projection_set = :projection_set
              AND projection_kind = :projection_kind
            """
            ),
            {"projection_set": projection_set, "projection_kind": projection_kind},
        )
        .mappings()
        .first()
    )
    if row is None or row["min_x"] is None:
        return None
    return {key: float(row[key]) for key in ("min_x", "max_x", "min_y", "max_y", "min_z", "max_z")}


def load_distinct_values(
    session: Session,
    *,
    column: str,
    projection_set: str,
    projection_kind_for_set: Any,
) -> list[str]:
    return load_filtered_distinct_values(
        session,
        column=column,
        where_sql=(
            "WHERE p.projection_set = :projection_set AND p.projection_kind = :projection_kind"
        ),
        params={
            "projection_set": projection_set,
            "projection_kind": projection_kind_for_set(projection_set),
        },
    )


def load_filtered_distinct_values(
    session: Session,
    *,
    column: str,
    where_sql: str,
    params: dict[str, Any],
) -> list[str]:
    rows = (
        session.execute(
            text(
                f"""
            SELECT DISTINCT {column} AS value
            FROM article_projections p
            JOIN articles a ON a.id = p.article_id
            JOIN article_embeddings e ON e.id = p.embedding_id
            LEFT JOIN semantic_point_analysis spa
              ON spa.article_id = p.article_id
             AND spa.projection_set = p.projection_set
            LEFT JOIN article_editorial_analysis aea
              ON aea.article_id = p.article_id
            {where_sql}
              AND {column} <> ''
            ORDER BY value ASC
            """
            ),
            params,
        )
        .scalars()
        .all()
    )
    return [str(value) for value in rows if value is not None]


def load_available_clusters(session: Session, *, projection_set: str) -> list[int]:
    rows = (
        session.execute(
            text(
                "SELECT cluster_id FROM semantic_clusters WHERE projection_set = :projection_set ORDER BY cluster_id ASC"
            ),
            {"projection_set": projection_set},
        )
        .scalars()
        .all()
    )
    return [int(value) for value in rows if value is not None]


def load_cluster_summaries(session: Session, *, projection_set: str) -> list[dict[str, Any]]:
    rows = (
        session.execute(
            text(
                """
            SELECT cluster_id, size, top_sources_json, source_count, source_dominance,
                   date_min, date_max, centroid_x, centroid_y, centroid_z,
                   representative_article_ids_json
            FROM semantic_clusters
            WHERE projection_set = :projection_set
            ORDER BY size DESC, cluster_id ASC
            """
            ),
            {"projection_set": projection_set},
        )
        .mappings()
        .all()
    )
    return [
        {
            "cluster_id": int(row["cluster_id"]),
            "size": int(row["size"]),
            "top_sources": json.loads(row["top_sources_json"] or "{}"),
            "source_count": int(row["source_count"] or 0),
            "source_dominance": float(row["source_dominance"] or 0.0),
            "date_min": row["date_min"] or "",
            "date_max": row["date_max"] or "",
            "centroid": {
                "x": float(row["centroid_x"] or 0.0),
                "y": float(row["centroid_y"] or 0.0),
                "z": float(row["centroid_z"] or 0.0),
            },
            "representative_article_ids": json.loads(
                row["representative_article_ids_json"] or "[]"
            ),
        }
        for row in rows
    ]


def build_editorial_review_flags(
    *,
    analysis_status: str,
    bias_label: str,
    bias_confidence: float,
    evidence_spans: list[dict],
    unclear_reasons: list[str],
    editorial_applicability: str,
) -> dict[str, bool]:
    missing_evidence = analysis_status == "completed" and not evidence_spans
    low_confidence = analysis_status == "completed" and bias_confidence < 0.45
    failed_analysis = analysis_status == "failed"
    unclear_bias = bias_label == "unclear"
    provider_missing = "provider_missing" in unclear_reasons
    mapping_loss = "mapping_loss" in unclear_reasons or "repair_data_loss" in unclear_reasons
    out_of_domain = editorial_applicability == "out_of_domain"
    pending_analysis = analysis_status == "pending"
    needs_review = any(
        [
            missing_evidence,
            low_confidence,
            failed_analysis,
            unclear_bias,
            provider_missing,
            mapping_loss,
            out_of_domain,
            pending_analysis,
        ]
    )
    return {
        "missing_evidence": missing_evidence,
        "low_confidence": low_confidence,
        "failed_analysis": failed_analysis,
        "unclear_bias": unclear_bias,
        "provider_missing": provider_missing,
        "mapping_loss": mapping_loss,
        "out_of_domain": out_of_domain,
        "pending_analysis": pending_analysis,
        "needs_review": needs_review,
    }


def parse_json_list(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def parse_json_scalar_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]
