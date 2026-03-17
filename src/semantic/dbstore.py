from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.core.text_normalization import normalize_text
from src.persistence.orm_models import ArticleORM
from src.semantic.contracts import (
    EmbeddingArtifact,
    NeighborArtifact,
    PointAnalysisArtifact,
    PointArtifact,
    SemanticArticle,
)
from src.semantic.project import project_embeddings

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_PROJECTION_KIND = "pca_2d"
DEFAULT_PROJECTION_SET = "pca_2d_latest"
DEFAULT_PROJECTION_VERSION = "v1"
DEFAULT_NEIGHBOR_LIMIT = 5
MIN_TEXT_LENGTH = 40

EMBEDDING_MODEL_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}

INIT_SQL_TEMPLATE = """
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


def embedding_dimensions_for_model(model: str) -> int:
    try:
        return EMBEDDING_MODEL_DIMENSIONS[model]
    except KeyError as exc:
        supported = ", ".join(sorted(EMBEDDING_MODEL_DIMENSIONS))
        raise ValueError(
            f"unsupported embedding model: {model!r}; supported models: {supported}"
        ) from exc


def render_init_sql(*, embedding_model: str) -> str:
    return INIT_SQL_TEMPLATE.format(embedding_dim=embedding_dimensions_for_model(embedding_model))


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
        elif current_dim != required_dim:
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
    session: Session, *, limit: int, max_chars: int, embedding_model: str = DEFAULT_EMBEDDING_MODEL
) -> list[SemanticCandidate]:
    rows = (
        session.query(ArticleORM)
        .order_by(ArticleORM.published_at.desc().nullslast(), ArticleORM.id.desc())
        .limit(limit * 4)
        .all()
    )
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
        if len(candidates) >= limit:
            break
    return candidates


def upsert_embeddings(
    session: Session,
    records: list[EmbeddingArtifact],
    *,
    content_hashes: dict[int, str],
    source_text_chars: dict[int, int],
) -> int:
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
    session: Session, *, projection_set: str | None = None
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
    if projection_set:
        sql += (
            " JOIN article_projections p"
            " ON p.embedding_id = e.id"
            " AND p.projection_set = :projection_set"
        )
        params["projection_set"] = projection_set
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
    session: Session, *, projection_set: str, projection_version: str = DEFAULT_PROJECTION_VERSION
) -> int:
    records = load_embedding_artifacts(session)
    points = project_embeddings(records)
    now = _utc_now()
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
                  :x, :y, NULL, :projected_at, :updated_at
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
                "projection_kind": DEFAULT_PROJECTION_KIND,
                "projection_version": projection_version,
                "x": point.x,
                "y": point.y,
                "projected_at": now,
                "updated_at": now,
            },
        )
    session.commit()
    return len(points)


def load_projected_points(
    session: Session,
    *,
    projection_set: str,
    include_neighbors: bool = False,
    neighbor_limit: int = DEFAULT_NEIGHBOR_LIMIT,
) -> list[PointArtifact]:
    rows = (
        session.execute(
            text(
                """
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
                   p.x, p.y
            FROM article_projections p
            JOIN article_embeddings e ON e.id = p.embedding_id
            JOIN articles a ON a.id = p.article_id
            WHERE p.projection_set = :projection_set
              AND p.projection_kind = :projection_kind
            ORDER BY a.published_at DESC NULLS LAST, a.id DESC
            """
            ),
            {"projection_set": projection_set, "projection_kind": DEFAULT_PROJECTION_KIND},
        )
        .mappings()
        .all()
    )
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


@dataclass
class ExplorerArticleDetailRecord:
    article: dict[str, Any]
    projection_set: str
    point: PointArtifact | None
    neighbors: list[NeighborArtifact]


def load_explorer_points_page(session: Session, *, filters: ExplorerFilters) -> ExplorerPointsPage:
    where_sql, params = _build_explorer_where_clause(filters)
    rows = (
        session.execute(
            text(
                f"""
            SELECT a.id AS article_id,
                   a.source,
                   a.title,
                   a.url,
                   COALESCE(a.published_at, '') AS published_at,
                   COALESCE(substr(CAST(a.published_at AS TEXT), 1, 10), '') AS published_date,
                   COALESCE(substr(CAST(a.published_at AS TEXT), 1, 10), '') AS display_date,
                   COALESCE(a.section, '') AS section,
                   COALESCE(e.summary_snippet, '') AS summary_snippet,
                   p.x,
                   p.y
            FROM article_projections p
            JOIN articles a ON a.id = p.article_id
            JOIN article_embeddings e ON e.id = p.embedding_id
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
                analysis=_analysis_for_neighbors(row["article_id"], neighbors),
            )
        )
    total = session.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM article_projections p
            JOIN articles a ON a.id = p.article_id
            JOIN article_embeddings e ON e.id = p.embedding_id
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
        available_clusters=[],
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
        "available_clusters": [],
    }


def load_explorer_article_detail(
    session: Session,
    *,
    article_id: int,
    projection_set: str,
) -> ExplorerArticleDetailRecord | None:
    row = (
        session.execute(
            text(
                """
            SELECT a.id AS article_id,
                   a.source,
                   a.title,
                   a.url,
                   COALESCE(a.published_at, '') AS published_at,
                   COALESCE(substr(CAST(a.published_at AS TEXT), 1, 10), '') AS published_date,
                   COALESCE(substr(CAST(a.published_at AS TEXT), 1, 10), '') AS display_date,
                   COALESCE(a.section, '') AS section,
                   COALESCE(a.summary, '') AS summary,
                   COALESCE(a.article_text, '') AS article_text,
                   p.x,
                   p.y,
                   COALESCE(e.summary_snippet, '') AS summary_snippet
            FROM articles a
            LEFT JOIN article_embeddings e ON e.article_id = a.id
            LEFT JOIN article_projections p
              ON p.article_id = a.id
             AND p.projection_set = :projection_set
             AND p.projection_kind = :projection_kind
            WHERE a.id = :article_id
            """
            ),
            {
                "article_id": article_id,
                "projection_set": projection_set,
                "projection_kind": DEFAULT_PROJECTION_KIND,
            },
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    neighbors = _safe_neighbors(session, article_id=article_id, limit=5)
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
            analysis=_analysis_for_neighbors(row["article_id"], neighbors),
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


def _build_explorer_where_clause(filters: ExplorerFilters) -> tuple[str, dict[str, Any]]:
    clauses = ["p.projection_set = :projection_set", "p.projection_kind = :projection_kind"]
    params: dict[str, Any] = {
        "projection_set": filters.projection_set,
        "projection_kind": DEFAULT_PROJECTION_KIND,
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
    if filters.search:
        clauses.append("(lower(a.title) LIKE :search OR lower(a.summary) LIKE :search)")
        params["search"] = f"%{filters.search.strip().lower()}%"
    if filters.cluster_id is not None:
        clauses.append("1 = 0")
    if filters.outlier_only:
        clauses.append("1 = 0")
    return "WHERE " + " AND ".join(clauses), params


def _load_projection_bounds(session: Session, *, projection_set: str) -> dict[str, float] | None:
    row = (
        session.execute(
            text(
                """
            SELECT MIN(x) AS min_x, MAX(x) AS max_x, MIN(y) AS min_y, MAX(y) AS max_y
            FROM article_projections
            WHERE projection_set = :projection_set
              AND projection_kind = :projection_kind
            """
            ),
            {"projection_set": projection_set, "projection_kind": DEFAULT_PROJECTION_KIND},
        )
        .mappings()
        .first()
    )
    if row is None or row["min_x"] is None:
        return None
    return {key: float(row[key]) for key in ("min_x", "max_x", "min_y", "max_y")}


def _load_distinct_values(session: Session, *, column: str, projection_set: str) -> list[str]:
    return _load_filtered_distinct_values(
        session,
        column=column,
        where_sql=(
            "WHERE p.projection_set = :projection_set AND p.projection_kind = :projection_kind"
        ),
        params={"projection_set": projection_set, "projection_kind": DEFAULT_PROJECTION_KIND},
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


def _analysis_for_neighbors(
    article_id: int,
    neighbors: list[NeighborArtifact],
) -> PointAnalysisArtifact:
    return PointAnalysisArtifact(
        article_id=article_id,
        cluster_id=None,
        cluster_size=0,
        is_outlier=False,
        source_neighbor_diversity=len({neighbor.source for neighbor in neighbors}),
        nearby_sources=sorted({neighbor.source for neighbor in neighbors}),
    )
