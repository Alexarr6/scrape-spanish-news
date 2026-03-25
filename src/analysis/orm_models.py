from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.analysis.editorial.orm import ArticleEditorialAnalysisORM
from src.persistence.orm import Base

__all__ = ["ArticleEditorialAnalysisORM"]


class ArticleEnrichmentRunORM(Base):
    __tablename__ = "article_enrichment_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    article_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), default="openrouter", nullable=False)
    model: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="started", nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)


class TagORM(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("tag_code", name="uq_tags_tag_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tag_code: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    tag_group: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parent_tag_id: Mapped[int | None] = mapped_column(ForeignKey("tags.id"), nullable=True)


class ArticleAnalysisORM(Base):
    __tablename__ = "article_analysis"
    __table_args__ = (UniqueConstraint("article_id", name="uq_article_analysis_article_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    article_type: Mapped[str] = mapped_column(String(40), nullable=False)
    article_type_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_event_coverage: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="es", nullable=False)
    primary_topic_tag_id: Mapped[int | None] = mapped_column(ForeignKey("tags.id"), nullable=True)
    key_phrases_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    claims_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EntityORM(Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("entity_type", "normalized_name", name="uq_entities_type_normalized_name"),
        UniqueConstraint("slug", name="uq_entities_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), default="", nullable=False)
    parent_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    canonical_source: Mapped[str] = mapped_column(String(40), default="rule", nullable=False)


class EntityAliasORM(Base):
    __tablename__ = "entity_aliases"
    __table_args__ = (
        UniqueConstraint(
            "entity_id", "normalized_alias", name="uq_entity_aliases_entity_normalized_alias"
        ),
        Index("ix_entity_aliases_normalized_alias", "normalized_alias"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(200), nullable=False)
    alias_type: Mapped[str] = mapped_column(String(40), default="surface", nullable=False)


class EntityMentionORM(Base):
    __tablename__ = "entity_mentions"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "entity_id",
            "mention_text_normalized",
            name="uq_entity_mentions_article_entity_mention",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    surface_form: Mapped[str] = mapped_column(String(200), nullable=False)
    mention_text_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title_hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    body_hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_char_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_char_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    role_hint: Mapped[str | None] = mapped_column(String(80), nullable=True)


class ArticleTagORM(Base):
    __tablename__ = "article_tags"
    __table_args__ = (UniqueConstraint("article_id", "tag_id", name="uq_article_tags_article_tag"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    assignment_source: Mapped[str] = mapped_column(String(40), default="hybrid", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class StoryClusterORM(Base):
    __tablename__ = "story_clusters"
    __table_args__ = (UniqueConstraint("cluster_key", name="uq_story_clusters_cluster_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cluster_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    event_date_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    event_date_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    first_article_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_article_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cluster_type: Mapped[str] = mapped_column(String(40), default="breaking_event", nullable=False)
    summary_headline: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    primary_tag_id: Mapped[int | None] = mapped_column(ForeignKey("tags.id"), nullable=True)
    article_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    clustering_version: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)


class ClusterMemberORM(Base):
    __tablename__ = "cluster_members"
    __table_args__ = (UniqueConstraint("article_id", name="uq_cluster_members_article_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("story_clusters.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    membership_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    membership_reason_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClusterEntityORM(Base):
    __tablename__ = "cluster_entities"
    __table_args__ = (
        UniqueConstraint("cluster_id", "entity_id", name="uq_cluster_entities_cluster_entity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("story_clusters.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    article_coverage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aggregate_relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
