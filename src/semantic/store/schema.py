from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.semantic.store.sql import split_sql

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

EMBEDDING_MODEL_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}

SCHEMA_SQL_TEMPLATE = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS article_embeddings (
  id BIGSERIAL PRIMARY KEY,
  article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  embedding_model TEXT NOT NULL,
  embedding_dim INTEGER NOT NULL,
  embedding VECTOR({embedding_dim}) NOT NULL,
  content_hash TEXT NOT NULL,
  source_text_chars INTEGER NOT NULL,
  summary_snippet TEXT NOT NULL DEFAULT '',
  embedded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_article_embeddings_article_id UNIQUE (article_id)
);

CREATE INDEX IF NOT EXISTS ix_article_embeddings_model ON article_embeddings (embedding_model);
CREATE INDEX IF NOT EXISTS ix_article_embeddings_updated_at ON article_embeddings (updated_at);

CREATE TABLE IF NOT EXISTS article_projections (
  id BIGSERIAL PRIMARY KEY,
  article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  embedding_id BIGINT NOT NULL REFERENCES article_embeddings(id) ON DELETE CASCADE,
  projection_set TEXT NOT NULL,
  projection_kind TEXT NOT NULL,
  projection_version TEXT NOT NULL,
  x DOUBLE PRECISION NOT NULL,
  y DOUBLE PRECISION NOT NULL,
  z DOUBLE PRECISION,
  projected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_article_projections_article_set UNIQUE (article_id, projection_set)
);

CREATE INDEX IF NOT EXISTS ix_article_projections_kind ON article_projections (projection_kind);
CREATE INDEX IF NOT EXISTS ix_article_projections_set ON article_projections (projection_set);
CREATE INDEX IF NOT EXISTS ix_article_projections_embedding_id
  ON article_projections (embedding_id);

CREATE TABLE IF NOT EXISTS semantic_point_analysis (
  id BIGSERIAL PRIMARY KEY,
  article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  projection_set TEXT NOT NULL,
  cluster_id INTEGER,
  cluster_size INTEGER NOT NULL DEFAULT 0,
  is_outlier BOOLEAN NOT NULL DEFAULT FALSE,
  local_density_distance DOUBLE PRECISION NOT NULL DEFAULT 0,
  source_neighbor_diversity INTEGER NOT NULL DEFAULT 0,
  nearby_sources_json TEXT NOT NULL DEFAULT '[]',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_semantic_point_analysis_article_set UNIQUE (article_id, projection_set)
);

CREATE INDEX IF NOT EXISTS ix_semantic_point_analysis_projection_set
  ON semantic_point_analysis (projection_set);
CREATE INDEX IF NOT EXISTS ix_semantic_point_analysis_cluster_id
  ON semantic_point_analysis (projection_set, cluster_id);

CREATE TABLE IF NOT EXISTS semantic_clusters (
  id BIGSERIAL PRIMARY KEY,
  projection_set TEXT NOT NULL,
  cluster_id INTEGER NOT NULL,
  size INTEGER NOT NULL,
  article_ids_json TEXT NOT NULL DEFAULT '[]',
  representative_article_ids_json TEXT NOT NULL DEFAULT '[]',
  top_sources_json TEXT NOT NULL DEFAULT '{{}}',
  source_count INTEGER NOT NULL DEFAULT 0,
  source_dominance DOUBLE PRECISION NOT NULL DEFAULT 0,
  date_min TEXT NOT NULL DEFAULT '',
  date_max TEXT NOT NULL DEFAULT '',
  centroid_x DOUBLE PRECISION NOT NULL DEFAULT 0,
  centroid_y DOUBLE PRECISION NOT NULL DEFAULT 0,
  centroid_z DOUBLE PRECISION NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_semantic_clusters_projection_cluster UNIQUE (projection_set, cluster_id)
);

CREATE INDEX IF NOT EXISTS ix_semantic_clusters_projection_set
  ON semantic_clusters (projection_set);
"""

HNSW_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS ix_article_embeddings_embedding_cosine_hnsw
ON article_embeddings USING hnsw (embedding vector_cosine_ops);
"""

VECTOR_TYPE_PATTERN = re.compile(r"^vector\((?P<dim>\d+)\)$")


@dataclass(frozen=True)
class SemanticWindow:
    """Inclusive UTC date window used by semantic sync/project/build flows."""

    date_from: str | None = None
    date_to: str | None = None


def resolve_semantic_window(
    *,
    days_back: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    today: date | None = None,
) -> SemanticWindow | None:
    if days_back is not None and days_back < 1:
        raise ValueError("days_back must be >= 1")
    if days_back is not None and (date_from or date_to):
        raise ValueError("days_back cannot be combined with explicit date_from/date_to")
    today = today or datetime.now(timezone.utc).date()
    if days_back is not None:
        date_to = today.isoformat()
        date_from = (today - timedelta(days=days_back - 1)).isoformat()
    if date_from:
        date.fromisoformat(date_from)
    if date_to:
        date.fromisoformat(date_to)
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from cannot be after date_to")
    if not date_from and not date_to:
        return None
    return SemanticWindow(date_from=date_from, date_to=date_to)


def apply_article_date_window(
    clauses: list[str], params: dict[str, Any], *, window: SemanticWindow | None
) -> None:
    if window is None:
        return
    if window.date_from:
        clauses.append("date(a.published_at) >= date(:window_date_from)")
        params["window_date_from"] = window.date_from
    if window.date_to:
        clauses.append("date(a.published_at) <= date(:window_date_to)")
        params["window_date_to"] = window.date_to


def embedding_dimensions_for_model(model: str) -> int:
    try:
        return EMBEDDING_MODEL_DIMENSIONS[model]
    except KeyError as exc:
        supported = ", ".join(sorted(EMBEDDING_MODEL_DIMENSIONS))
        raise ValueError(
            f"unsupported embedding model: {model!r}; supported models: {supported}"
        ) from exc


def render_init_sql(*, embedding_model: str) -> str:
    return SCHEMA_SQL_TEMPLATE.format(embedding_dim=embedding_dimensions_for_model(embedding_model))


def render_additive_schema_sql(*, embedding_model: str) -> str:
    return SCHEMA_SQL_TEMPLATE.format(embedding_dim=embedding_dimensions_for_model(embedding_model))


def init_pgvector_schema(
    engine: Engine,
    *,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ensure_ann_index: bool = False,
) -> None:
    required_dim = embedding_dimensions_for_model(embedding_model)
    with engine.begin() as conn:
        current_dim = get_embedding_vector_dimensions(conn)
        if current_dim is None:
            for statement in split_sql(render_init_sql(embedding_model=embedding_model)):
                conn.execute(text(statement))
        else:
            if current_dim != required_dim:
                row_count = conn.execute(text("SELECT COUNT(*) FROM article_embeddings")).scalar_one()
                if row_count:
                    raise RuntimeError(
                        "article_embeddings.embedding uses "
                        f"VECTOR({current_dim}) but model {embedding_model!r} "
                        f"requires VECTOR({required_dim}). "
                        "Rebuild or clear semantic embeddings before switching embedding models."
                    )
                conn.execute(
                    text(
                        "ALTER TABLE article_embeddings "
                        f"ALTER COLUMN embedding TYPE VECTOR({required_dim})"
                    )
                )
            for statement in split_sql(render_additive_schema_sql(embedding_model=embedding_model)):
                conn.execute(text(statement))
        if ensure_ann_index:
            conn.execute(text(HNSW_INDEX_SQL))


def ensure_vector_index(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(HNSW_INDEX_SQL))


def get_embedding_vector_dimensions(bind: Engine | Session | Any) -> int | None:
    executor = bind
    if isinstance(bind, Session):
        executor = bind.connection()
    row = executor.execute(
        text(
            """
            SELECT format_type(a.atttypid, a.atttypmod) AS vector_type
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = current_schema()
              AND c.relname = 'article_embeddings'
              AND a.attname = 'embedding'
              AND a.attnum > 0
              AND NOT a.attisdropped
            """
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    match = VECTOR_TYPE_PATTERN.match(row)
    if not match:
        raise RuntimeError(f"unexpected article_embeddings.embedding type: {row}")
    return int(match.group("dim"))

