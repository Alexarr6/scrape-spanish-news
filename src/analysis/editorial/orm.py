from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.orm import Base


class ArticleEditorialAnalysisORM(Base):
    __tablename__ = "article_editorial_analysis"
    __table_args__ = (
        UniqueConstraint("article_id", name="uq_article_editorial_analysis_article_id"),
        Index("ix_article_editorial_analysis_bias_label", "bias_label"),
        Index("ix_article_editorial_analysis_article_type", "article_type"),
        Index("ix_article_editorial_analysis_analyzed_at", "analyzed_at"),
        Index("ix_article_editorial_analysis_content_hash", "content_hash"),
        Index("ix_article_editorial_analysis_analysis_status", "analysis_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    article_type: Mapped[str] = mapped_column(String(40), nullable=False)
    article_type_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bias_label: Mapped[str] = mapped_column(String(40), nullable=False)
    bias_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bias_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tone_emotional: Mapped[str] = mapped_column(String(40), nullable=False)
    tone_target: Mapped[str] = mapped_column(String(40), nullable=False)
    opinionatedness: Mapped[str] = mapped_column(String(40), nullable=False)
    sensationalism: Mapped[str] = mapped_column(String(40), nullable=False)
    rhetorical_certainty: Mapped[str] = mapped_column(String(40), nullable=False)
    editorial_applicability: Mapped[str] = mapped_column(String(40), default="full", nullable=False)
    editorial_applicability_reason: Mapped[str] = mapped_column(
        String(80), default="general_editorial_content", nullable=False
    )
    provider_failure_class: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    analysis_path: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    unclear_reasons_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    article_type_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    bias_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    tone_emotional_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    tone_target_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    opinionatedness_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    sensationalism_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    rhetorical_certainty_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    framing_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    framing_devices_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    evidence_spans_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    diagnostics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    failure_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    model_provider: Mapped[str] = mapped_column(String(40), default="openrouter", nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)
    schema_version: Mapped[str] = mapped_column(
        String(80), default="editorial-analysis-v1", nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    source_text_version: Mapped[str] = mapped_column(
        String(80), default="title_summary_body_v1", nullable=False
    )
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
