"""Database-backed semantic storage, projection refresh, and explorer read-side helpers."""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.core.text_normalization import normalize_text
from src.persistence.orm_models import ArticleORM
from src.semantic.analyze import analyze_points
from src.semantic.contracts import (
    EmbeddingArtifact,
    NeighborArtifact,
    PointAnalysisArtifact,
    PointArtifact,
    SemanticArticle,
)
from src.semantic.project import project_embeddings

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_PROJECTION_KIND = "pca_3d"
DEFAULT_PROJECTION_SET = "pca_3d_latest"
DEFAULT_PROJECTION_VERSION = "v1"
DEFAULT_NEIGHBOR_LIMIT = 5
MIN_TEXT_LENGTH = 40


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
    """Resolve CLI-style date flags into one validated inclusive window.

    `days_back` means an inclusive UTC range ending on `today`. Explicit
    `date_from`/`date_to` can be used independently or together, but they cannot
    be combined with `days_back`. Returning ``None`` keeps the old full-history
    behavior for callers that want no date filter at all.
    """

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


def _apply_article_date_window(
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


@dataclass
class SemanticCandidate:
    article: SemanticArticle
    assembled_text: str
    content_hash: str


@dataclass
class NeighborRow:
    article_id: int
    similarity: float
    source: str = ""
    title: str = ""
    url: str = ""
    published_at: str = ""
    published_date: str = ""
    display_date: str = ""
    section: str = ""
    summary_snippet: str = ""

    def to_artifact(self) -> NeighborArtifact:
        return NeighborArtifact(
            article_id=self.article_id,
            similarity=self.similarity,
            source=self.source,
            title=self.title,
            url=self.url,
            published_at=self.published_at,
            published_date=self.published_date,
            display_date=self.display_date,
            section=self.section,
            summary_snippet=self.summary_snippet,
        )


@dataclass
class SeedArticleRow:
    article_id: int
    source: str
    title: str
    url: str
    published_at: str
    published_date: str
    display_date: str
    section: str
    summary_snippet: str
    embedding_model: str


@dataclass(frozen=True)
class StoryClusterPriorityGroup:
    cluster_id: int
    article_count: int
    article_ids: list[int]


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
            for statement in _split_sql(render_init_sql(embedding_model=embedding_model)):
                conn.execute(text(statement))
        else:
            if current_dim != required_dim:
                row_count = conn.execute(
                    text("SELECT COUNT(*) FROM article_embeddings")
                ).scalar_one()
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
            for statement in _split_sql(
                render_additive_schema_sql(embedding_model=embedding_model)
            ):
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


def build_candidate(article_row: ArticleORM, *, max_chars: int) -> SemanticCandidate | None:
    """Build one embedding candidate or skip rows that do not have enough text."""

    article = SemanticArticle(
        article_id=article_row.id,
        source=article_row.source,
        title=article_row.title,
        url=article_row.url,
        published_at=article_row.published_at.isoformat() if article_row.published_at else "",
        section=article_row.section or "",
        summary=article_row.summary or "",
        article_text=article_row.article_text or "",
    )
    assembled_text = assemble_article_text(article, max_chars=max_chars)
    if len(assembled_text) < MIN_TEXT_LENGTH:
        return None
    return SemanticCandidate(
        article=article,
        assembled_text=assembled_text,
        content_hash=content_hash_for_text(assembled_text),
    )


def assemble_article_text(article: SemanticArticle, *, max_chars: int) -> str:
    """Assemble normalized source/context/title/body text for embedding generation."""

    context = " | ".join(
        part for part in [normalize_text(article.source), normalize_text(article.section)] if part
    )
    parts = [
        context,
        normalize_text(article.title),
        normalize_text(article.summary),
        normalize_text(article.article_text),
    ]
    text_value = "\n\n".join(part for part in parts if part)
    return text_value[:max_chars].strip()


def content_hash_for_text(text_value: str) -> str:
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


def summary_snippet(article: SemanticArticle, *, max_chars: int = 240) -> str:
    summary = normalize_text(article.summary)
    if summary:
        return summary[:max_chars]
    return normalize_text(article.article_text)[:max_chars]


def select_embedding_candidates(
    session: Session,
    *,
    limit: int,
    max_chars: int,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    window: SemanticWindow | None = None,
    prioritize_story_members: bool = False,
    priority_story_cluster_min_size: int = 2,
) -> list[SemanticCandidate]:
    """Select recent articles whose semantic embedding is missing or stale.

    The query intentionally over-fetches recent article rows, then filters in
    Python so short/empty articles and unchanged content hashes do not consume
    embedding requests. When requested, recently clustered story members are
    drained ahead of plain-recency rows so Stories freshness gets semantic
    coverage sooner.
    """

    query = session.query(ArticleORM)
    if window and window.date_from:
        query = query.filter(text("date(published_at) >= date(:window_date_from)")).params(
            window_date_from=window.date_from
        )
    if window and window.date_to:
        query = query.filter(text("date(published_at) <= date(:window_date_to)")).params(
            window_date_to=window.date_to
        )
    rows = (
        query.order_by(ArticleORM.published_at.desc().nullslast(), ArticleORM.id.desc())
        .limit(limit * 4)
        .all()
    )
    priority_groups = (
        _load_story_cluster_priority_groups(
            session,
            article_ids=[row.id for row in rows],
            min_article_count=priority_story_cluster_min_size,
        )
        if prioritize_story_members and rows
        else []
    )
    qualifying_story_member_ids = {
        article_id for group in priority_groups for article_id in group.article_ids
    }
    candidates: list[SemanticCandidate] = []
    for row in rows:
        candidate = build_candidate(row, max_chars=max_chars)
        if candidate is None:
            continue
        existing = (
            session.execute(
                text(
                    "SELECT content_hash, embedding_model "
                    "FROM article_embeddings WHERE article_id = :article_id"
                ),
                {"article_id": row.id},
            )
            .mappings()
            .first()
        )
        if (
            existing
            and existing["content_hash"] == candidate.content_hash
            and existing["embedding_model"] == embedding_model
        ):
            continue
        candidates.append(candidate)

    if prioritize_story_members:
        ordered_article_ids = select_cluster_aware_article_ids(
            [candidate.article for candidate in candidates],
            limit=limit,
            priority_groups=priority_groups,
        )
        by_article_id = {candidate.article.article_id: candidate for candidate in candidates}
        return [
            by_article_id[article_id]
            for article_id in ordered_article_ids
            if article_id in by_article_id
        ]
    ordered_candidates = _source_balance_candidates(candidates)
    return ordered_candidates[:limit]


def upsert_embeddings(
    session: Session,
    records: list[EmbeddingArtifact],
    *,
    content_hashes: dict[int, str],
    source_text_chars: dict[int, int],
) -> int:
    """Upsert one embedding batch while enforcing schema/model dimension alignment."""

    if not records:
        return 0
    model_names = {record.embedding_model for record in records}
    if len(model_names) != 1:
        raise ValueError(
            f"mixed embedding models in one upsert are not supported: {sorted(model_names)}"
        )
    expected_model = records[0].embedding_model
    expected_dim = embedding_dimensions_for_model(expected_model)
    schema_dim = get_embedding_vector_dimensions(session)
    if schema_dim is None:
        raise RuntimeError("article_embeddings table is missing; run semantic-db-init first")
    if schema_dim != expected_dim:
        raise RuntimeError(
            "article_embeddings.embedding uses "
            f"VECTOR({schema_dim}) but model {expected_model!r} returns {expected_dim} dimensions"
        )

    updated = 0
    now = _utc_now()
    for record in records:
        if len(record.embedding) != expected_dim:
            raise ValueError(
                f"embedding length mismatch for model {expected_model!r}: "
                f"expected {expected_dim}, got {len(record.embedding)}"
            )
        embedding_literal = vector_literal(record.embedding)
        session.execute(
            text(
                """
                INSERT INTO article_embeddings (
                  article_id, embedding_model, embedding_dim, embedding, content_hash,
                  source_text_chars, summary_snippet, embedded_at, updated_at
                ) VALUES (
                  :article_id, :embedding_model, :embedding_dim,
                  CAST(:embedding AS vector), :content_hash,
                  :source_text_chars, :summary_snippet, :embedded_at, :updated_at
                )
                ON CONFLICT (article_id) DO UPDATE SET
                  embedding_model = EXCLUDED.embedding_model,
                  embedding_dim = EXCLUDED.embedding_dim,
                  embedding = EXCLUDED.embedding,
                  content_hash = EXCLUDED.content_hash,
                  source_text_chars = EXCLUDED.source_text_chars,
                  summary_snippet = EXCLUDED.summary_snippet,
                  embedded_at = EXCLUDED.embedded_at,
                  updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "article_id": record.article_id,
                "embedding_model": record.embedding_model,
                "embedding_dim": len(record.embedding),
                "embedding": embedding_literal,
                "content_hash": content_hashes[record.article_id],
                "source_text_chars": source_text_chars[record.article_id],
                "summary_snippet": record.summary_snippet,
                "embedded_at": now,
                "updated_at": now,
            },
        )
        updated += 1
    session.commit()
    return updated


def load_embedding_artifacts(
    session: Session,
    *,
    projection_set: str | None = None,
    window: SemanticWindow | None = None,
) -> list[EmbeddingArtifact]:
    sql = """
    SELECT a.id AS article_id, a.source, a.title, a.url,
           COALESCE(
             to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SSOF'),
             ''
           ) AS published_at,
           a.section, e.summary_snippet, e.source_text_chars, e.embedding_model,
           e.embedding::text AS embedding_text
    FROM article_embeddings e
    JOIN articles a ON a.id = e.article_id
    """
    params: dict[str, Any] = {}
    clauses: list[str] = []
    if projection_set:
        sql += (
            " JOIN article_projections p"
            " ON p.embedding_id = e.id"
            " AND p.projection_set = :projection_set"
        )
        params["projection_set"] = projection_set
    _apply_article_date_window(clauses, params, window=window)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY a.published_at DESC NULLS LAST, a.id DESC"
    rows = session.execute(text(sql), params).mappings().all()
    artifacts: list[EmbeddingArtifact] = []
    for row in rows:
        artifacts.append(
            EmbeddingArtifact(
                article_id=row["article_id"],
                source=row["source"],
                title=row["title"],
                url=row["url"],
                published_at=row["published_at"] or "",
                section=row["section"] or "",
                summary_snippet=row["summary_snippet"] or "",
                text_length=row["source_text_chars"] or 0,
                embedding_model=row["embedding_model"],
                embedding=parse_vector_text(row["embedding_text"]),
            )
        )
    return artifacts


def refresh_projection_set(
    session: Session,
    *,
    projection_set: str,
    projection_version: str = DEFAULT_PROJECTION_VERSION,
    window: SemanticWindow | None = None,
) -> int:
    """Rebuild one projection set and replace its derived explorer-side analysis.

    This is destructive per projection set on purpose: persisted coordinates,
    point-analysis rows, and cluster summaries for the named set are cleared and
    recomputed from the currently stored embeddings.
    """

    projection_kind = projection_kind_for_set(projection_set)
    embeddings = load_embedding_artifacts(session, window=window)
    points = project_embeddings(
        embeddings,
        dimensions=3 if projection_kind == "pca_3d" else 2,
    )
    now = _utc_now()
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


def projection_kind_for_set(projection_set: str) -> str:
    if projection_set.startswith("pca_2d"):
        return "pca_2d"
    if projection_set.startswith("pca_3d"):
        return "pca_3d"
    return DEFAULT_PROJECTION_KIND


def load_projected_points(
    session: Session,
    *,
    projection_set: str,
    include_neighbors: bool = False,
    neighbor_limit: int = DEFAULT_NEIGHBOR_LIMIT,
    window: SemanticWindow | None = None,
) -> list[PointArtifact]:
    """Load explorer-ready projected points, optionally hydrating nearest neighbors."""

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
                   COALESCE(spa.nearby_sources_json, '[]') AS nearby_sources_json
            FROM article_projections p
            JOIN article_embeddings e ON e.id = p.embedding_id
            JOIN articles a ON a.id = p.article_id
            LEFT JOIN semantic_point_analysis spa
              ON spa.article_id = p.article_id
             AND spa.projection_set = p.projection_set
    """
    params = {"projection_set": projection_set, "projection_kind": projection_kind}
    clauses = [
        "p.projection_set = :projection_set",
        "p.projection_kind = :projection_kind",
    ]
    _apply_article_date_window(clauses, params, window=window)
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
            analysis=_analysis_for_row(row, neighbors=[]),
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


def load_seed_article(session: Session, *, article_id: int) -> SeedArticleRow | None:
    row = (
        session.execute(
            text(
                """
            SELECT a.id AS article_id,
                   a.source,
                   a.title,
                   a.url,
                   COALESCE(
                     to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SSOF'),
                     ''
                   ) AS published_at,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '')
                     AS published_date,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '')
                     AS display_date,
                   COALESCE(a.section, '') AS section,
                   COALESCE(e.summary_snippet, '') AS summary_snippet,
                   COALESCE(e.embedding_model, '') AS embedding_model
            FROM articles a
            LEFT JOIN article_embeddings e ON e.article_id = a.id
            WHERE a.id = :article_id
            """
            ),
            {"article_id": article_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    return SeedArticleRow(**row)


def nearest_neighbors(session: Session, *, article_id: int, limit: int) -> list[NeighborRow]:
    rows = (
        session.execute(
            text(
                """
            SELECT other.article_id,
                   1 - (other.embedding <=> seed.embedding) AS similarity,
                   a.source,
                   a.title,
                   a.url,
                   COALESCE(
                     to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SSOF'),
                     ''
                   ) AS published_at,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '')
                     AS published_date,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '')
                     AS display_date,
                   COALESCE(a.section, '') AS section,
                   COALESCE(other.summary_snippet, '') AS summary_snippet
            FROM article_embeddings seed
            JOIN article_embeddings other ON other.article_id <> seed.article_id
            JOIN articles a ON a.id = other.article_id
            WHERE seed.article_id = :article_id
              AND other.embedding_model = seed.embedding_model
            ORDER BY other.embedding <=> seed.embedding
            LIMIT :limit
            """
            ),
            {"article_id": article_id, "limit": limit},
        )
        .mappings()
        .all()
    )
    return [
        NeighborRow(
            article_id=row["article_id"],
            similarity=float(row["similarity"]),
            source=row["source"] or "",
            title=row["title"] or "",
            url=row["url"] or "",
            published_at=row["published_at"] or "",
            published_date=row["published_date"] or "",
            display_date=row["display_date"] or "",
            section=row["section"] or "",
            summary_snippet=row["summary_snippet"] or "",
        )
        for row in rows
    ]


def load_neighbors_for_articles(
    session: Session, *, article_ids: list[int], limit: int = DEFAULT_NEIGHBOR_LIMIT
) -> dict[int, list[NeighborArtifact]]:
    return {
        article_id: [
            row.to_artifact()
            for row in nearest_neighbors(session, article_id=article_id, limit=limit)
        ]
        for article_id in article_ids
    }


def parse_vector_text(value: str) -> list[float]:
    stripped = value.strip().strip("[]")
    if not stripped:
        return []
    return [float(part) for part in stripped.split(",")]


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(_format_float(value) for value in values) + "]"


def _format_float(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("embedding contains non-finite values")
    return format(float(value), ".12g")


def _split_sql(sql_blob: str) -> list[str]:
    return [part.strip() for part in sql_blob.split(";") if part.strip()]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ExplorerFilters:
    projection_set: str = DEFAULT_PROJECTION_SET
    limit: int = 250
    source: str | None = None
    section: str | None = None
    cluster_id: int | None = None
    story_cluster_id: int | None = None
    visual_mode: str | None = None
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


@dataclass
class ExplorerArticleDetailRecord:
    article: dict[str, Any]
    projection_set: str
    point: PointArtifact | None
    neighbors: list[NeighborArtifact]


def select_source_balanced_article_ids(
    records: Sequence[SemanticArticle | EmbeddingArtifact | PointArtifact], *, limit: int
) -> list[int]:
    """Pick a bounded article slice without letting one source win by recency alone."""

    if limit <= 0:
        return []
    buckets: dict[str, list[int]] = defaultdict(list)
    source_order: list[str] = []
    for record in records:
        source = getattr(record, "source", "") or ""
        article_id = int(getattr(record, "article_id"))
        if source not in buckets:
            source_order.append(source)
        buckets[source].append(article_id)

    selected: list[int] = []
    while len(selected) < limit and source_order:
        next_round: list[str] = []
        for source in source_order:
            bucket = buckets[source]
            if bucket:
                selected.append(bucket.pop(0))
                if len(selected) >= limit:
                    break
            if bucket:
                next_round.append(source)
        source_order = next_round
    return selected


def select_cluster_aware_article_ids(
    records: Sequence[SemanticArticle | EmbeddingArtifact | PointArtifact],
    *,
    limit: int,
    priority_groups: Sequence[StoryClusterPriorityGroup] | None = None,
) -> list[int]:
    """Reserve room for complete qualifying story clusters before remainder fill."""

    if limit <= 0:
        return []
    record_ids = [int(getattr(record, "article_id")) for record in records]
    record_id_set = set(record_ids)
    selected: list[int] = []
    selected_set: set[int] = set()

    for group in priority_groups or []:
        cluster_ids = [
            article_id for article_id in group.article_ids if article_id in record_id_set
        ]
        if len(cluster_ids) != group.article_count:
            continue
        if len(selected) + len(cluster_ids) > limit:
            continue
        for article_id in cluster_ids:
            if article_id not in selected_set:
                selected.append(article_id)
                selected_set.add(article_id)

    remainder_records = [
        record for record in records if int(getattr(record, "article_id")) not in selected_set
    ]
    selected.extend(
        select_source_balanced_article_ids(remainder_records, limit=max(0, limit - len(selected)))
    )
    return selected[:limit]


def _load_story_cluster_priority_groups(
    session: Session, *, article_ids: list[int], min_article_count: int = 2
) -> list[StoryClusterPriorityGroup]:
    if not article_ids:
        return []
    placeholders = ", ".join(f":article_id_{index}" for index in range(len(article_ids)))
    params = {f"article_id_{index}": article_id for index, article_id in enumerate(article_ids)}
    params["min_article_count"] = min_article_count
    rows = (
        session.execute(
            text(
                f"""
                SELECT sc.id AS cluster_id,
                       sc.article_count AS article_count,
                       cm.article_id AS article_id
                FROM story_clusters sc
                JOIN cluster_members cm ON cm.cluster_id = sc.id
                WHERE sc.article_count >= :min_article_count
                  AND cm.article_id IN ({placeholders})
                ORDER BY sc.last_article_published_at DESC NULLS LAST,
                         sc.id ASC,
                         cm.article_id ASC
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    grouped: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    for row in rows:
        cluster_id = int(row["cluster_id"])
        if cluster_id not in grouped:
            grouped[cluster_id] = {
                "article_count": int(row["article_count"]),
                "article_ids": [],
            }
            order.append(cluster_id)
        grouped[cluster_id]["article_ids"].append(int(row["article_id"]))
    return [
        StoryClusterPriorityGroup(
            cluster_id=cluster_id,
            article_count=grouped[cluster_id]["article_count"],
            article_ids=grouped[cluster_id]["article_ids"],
        )
        for cluster_id in order
    ]


def _source_balance_candidates(candidates: list[SemanticCandidate]) -> list[SemanticCandidate]:
    if not candidates:
        return []
    article_ids = select_source_balanced_article_ids(
        [candidate.article for candidate in candidates], limit=len(candidates)
    )
    by_article_id = {candidate.article.article_id: candidate for candidate in candidates}
    return [by_article_id[article_id] for article_id in article_ids if article_id in by_article_id]


def _session_dialect_name(session: Session | Any) -> str:
    bind = getattr(session, "bind", None)
    if bind is None and hasattr(session, "get_bind"):
        try:
            bind = session.get_bind()
        except Exception:
            bind = None
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", "postgresql")


def _explorer_published_at_sql(*, dialect_name: str) -> str:
    if dialect_name == "sqlite":
        return """COALESCE(CAST(a.published_at AS TEXT), '') AS published_at,
                   COALESCE(substr(CAST(a.published_at AS TEXT), 1, 10), '') AS published_date,
                   COALESCE(substr(CAST(a.published_at AS TEXT), 1, 10), '') AS display_date"""
    return """COALESCE(
                       to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SSOF'),
                       ''
                   ) AS published_at,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '') AS published_date,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '') AS display_date"""


def load_explorer_points_page(session: Session, *, filters: ExplorerFilters) -> ExplorerPointsPage:
    """Return the semantic explorer page payload plus derived filter metadata.

    The response is intentionally richer than a plain point list because the UI
    expects bounds, available filter values, and cluster summaries in the same
    request.
    """

    projection_kind = projection_kind_for_set(filters.projection_set)
    where_sql, params = _build_explorer_where_clause(filters, projection_kind=projection_kind)
    published_at_sql = _explorer_published_at_sql(dialect_name=_session_dialect_name(session))
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
                   COALESCE(spa.nearby_sources_json, '[]') AS nearby_sources_json
            FROM article_projections p
            JOIN articles a ON a.id = p.article_id
            JOIN article_embeddings e ON e.id = p.embedding_id
            LEFT JOIN semantic_point_analysis spa
              ON spa.article_id = p.article_id
             AND spa.projection_set = p.projection_set
            {where_sql}
            ORDER BY a.published_at DESC, a.id DESC
            LIMIT :limit
            """
            ),
            {**params, "limit": filters.limit},
        )
        .mappings()
        .all()
    )
    story_cluster_ids_by_article = _load_story_cluster_memberships(
        session,
        article_ids=[int(row["article_id"]) for row in rows],
    )
    items: list[PointArtifact] = []
    for row in rows:
        neighbors = _safe_neighbors(session, article_id=row["article_id"], limit=3)
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
                analysis=_analysis_for_row(
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
        bounds=_load_projection_bounds(session, projection_set=filters.projection_set),
        available_sources=_load_filtered_distinct_values(
            session,
            column="a.source",
            where_sql=where_sql,
            params=params,
        ),
        available_sections=_load_filtered_distinct_values(
            session,
            column="a.section",
            where_sql=where_sql,
            params=params,
        ),
        available_clusters=_load_available_clusters(session, projection_set=filters.projection_set),
        cluster_summaries=_load_cluster_summaries(session, projection_set=filters.projection_set),
    )


def load_explorer_filter_options(session: Session, *, projection_set: str) -> dict[str, Any]:
    return {
        "projection_set": projection_set,
        "available_sources": _load_distinct_values(
            session, column="a.source", projection_set=projection_set
        ),
        "available_sections": _load_distinct_values(
            session, column="a.section", projection_set=projection_set
        ),
        "available_clusters": _load_available_clusters(session, projection_set=projection_set),
        "cluster_summaries": _load_cluster_summaries(session, projection_set=projection_set),
    }


def load_explorer_article_detail(
    session: Session,
    *,
    article_id: int,
    projection_set: str,
) -> ExplorerArticleDetailRecord | None:
    projection_kind = projection_kind_for_set(projection_set)
    published_at_sql = _explorer_published_at_sql(dialect_name=_session_dialect_name(session))
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
                   COALESCE(spa.nearby_sources_json, '[]') AS nearby_sources_json
            FROM articles a
            LEFT JOIN article_embeddings e ON e.article_id = a.id
            LEFT JOIN article_projections p
              ON p.article_id = a.id
             AND p.projection_set = :projection_set
             AND p.projection_kind = :projection_kind
            LEFT JOIN semantic_point_analysis spa
              ON spa.article_id = a.id
             AND spa.projection_set = :projection_set
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
    neighbors = _safe_neighbors(session, article_id=article_id, limit=5)
    story_cluster_ids_by_article = _load_story_cluster_memberships(session, article_ids=[article_id])
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
            analysis=_analysis_for_row(
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


def _load_projection_bounds(session: Session, *, projection_set: str) -> dict[str, float] | None:
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


def _load_distinct_values(session: Session, *, column: str, projection_set: str) -> list[str]:
    return _load_filtered_distinct_values(
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


def _load_filtered_distinct_values(
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


def _safe_neighbors(session: Session, *, article_id: int, limit: int) -> list[NeighborArtifact]:
    try:
        return [
            row.to_artifact()
            for row in nearest_neighbors(session, article_id=article_id, limit=limit)
        ]
    except Exception:
        return []


def _load_story_cluster_memberships(
    session: Session, *, article_ids: list[int]
) -> dict[int, list[int]]:
    if not article_ids:
        return {}
    placeholders = ", ".join(f":article_id_{index}" for index in range(len(article_ids)))
    params = {f"article_id_{index}": article_id for index, article_id in enumerate(article_ids)}
    rows = (
        session.execute(
            text(
                f"""
                SELECT article_id, cluster_id
                FROM cluster_members
                WHERE article_id IN ({placeholders})
                ORDER BY article_id ASC, cluster_id ASC
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    memberships: dict[int, list[int]] = {int(article_id): [] for article_id in article_ids}
    for row in rows:
        memberships.setdefault(int(row["article_id"]), []).append(int(row["cluster_id"]))
    return memberships


def _persist_projection_analysis(
    session: Session,
    *,
    projection_set: str,
    points: list[PointArtifact],
    embeddings: list[EmbeddingArtifact],
) -> None:
    analysis = analyze_points(points, embeddings)
    analysis_by_id = {point.article_id: point for point in analysis.points}
    now = _utc_now()
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


def _load_available_clusters(session: Session, *, projection_set: str) -> list[int]:
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


def _load_cluster_summaries(session: Session, *, projection_set: str) -> list[dict[str, Any]]:
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


def _analysis_for_row(
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
