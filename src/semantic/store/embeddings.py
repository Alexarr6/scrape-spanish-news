from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.text_normalization import normalize_text
from src.persistence.orm_models import ArticleORM
from src.semantic.contracts import EmbeddingArtifact, NeighborArtifact, SemanticArticle
from src.semantic.store.schema import (
    DEFAULT_EMBEDDING_MODEL,
    SemanticWindow,
    apply_article_date_window,
    embedding_dimensions_for_model,
    get_embedding_vector_dimensions,
)
from src.semantic.store.sql import parse_vector_text, utc_now, vector_literal
from src.semantic.store.story_priority import (
    load_story_cluster_priority_groups,
    select_cluster_aware_article_ids,
    source_balance_candidates,
)

DEFAULT_NEIGHBOR_LIMIT = 5
MIN_TEXT_LENGTH = 40


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
    session: Session,
    *,
    limit: int,
    max_chars: int,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    window: SemanticWindow | None = None,
    prioritize_story_members: bool = False,
    priority_story_cluster_min_size: int = 2,
) -> list[SemanticCandidate]:
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
        load_story_cluster_priority_groups(
            session,
            article_ids=[row.id for row in rows],
            min_article_count=priority_story_cluster_min_size,
        )
        if prioritize_story_members and rows
        else []
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
    return source_balance_candidates(candidates)[:limit]


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
    now = utc_now()
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
    apply_article_date_window(clauses, params, window=window)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY a.published_at DESC NULLS LAST, a.id DESC"
    rows = session.execute(text(sql), params).mappings().all()
    return [
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
        for row in rows
    ]


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

