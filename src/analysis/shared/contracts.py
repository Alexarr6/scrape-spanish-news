from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.analysis.editorial.core import (
    BIAS_LABELS,
    EDITORIAL_ANALYSIS_STATUSES,
    EDITORIAL_APPLICABILITY_REASONS,
    EDITORIAL_APPLICABILITY_VALUES,
    EDITORIAL_ARTICLE_TYPES,
    EDITORIAL_DIMENSION_STATUS_VALUES,
    EVIDENCE_SPAN_TYPES,
    FRAMING_DEVICE_VALUES,
    OPINIONATEDNESS_VALUES,
    RHETORICAL_CERTAINTY_VALUES,
    SENSATIONALISM_VALUES,
    TONE_EMOTIONAL_VALUES,
    TONE_TARGET_VALUES,
    ArticleEditorialAnalysisPayload,
    ArticleEditorialAnalysisRawPayload,
    ArticleEditorialEvidenceSpan,
    EditorialAnalysisDiagnostics,
    EditorialCompletedPersistence,
    EditorialDimensionDiagnostic,
    EditorialFailurePersistence,
)
from src.analysis.shared.taxonomy import validate_tag_codes

__all__ = [
    "BIAS_LABELS",
    "EDITORIAL_ANALYSIS_STATUSES",
    "EDITORIAL_APPLICABILITY_REASONS",
    "EDITORIAL_APPLICABILITY_VALUES",
    "EDITORIAL_ARTICLE_TYPES",
    "EDITORIAL_DIMENSION_STATUS_VALUES",
    "EVIDENCE_SPAN_TYPES",
    "FRAMING_DEVICE_VALUES",
    "OPINIONATEDNESS_VALUES",
    "RHETORICAL_CERTAINTY_VALUES",
    "SENSATIONALISM_VALUES",
    "TONE_EMOTIONAL_VALUES",
    "TONE_TARGET_VALUES",
    "ArticleEditorialAnalysisPayload",
    "ArticleEditorialAnalysisRawPayload",
    "ArticleEditorialEvidenceSpan",
    "EditorialCompletedPersistence",
    "EditorialAnalysisDiagnostics",
    "EditorialDimensionDiagnostic",
    "EditorialFailurePersistence",
]

ARTICLE_TYPES = (
    "news_report",
    "live_blog",
    "analysis",
    "opinion",
    "editorial",
    "interview",
    "feature",
    "explainer",
    "other",
)
class ArticleAnalysisExtractedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: Literal[
        "politician",
        "political_party",
        "person",
        "organization",
        "institution",
        "country",
        "region_city",
        "company",
        "event",
    ]
    canonical_name: str = Field(min_length=2, max_length=200)
    aliases: list[str] = Field(default_factory=list, max_length=5)
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    role_hint: str | None = Field(default=None, max_length=80)


class ArticleEnrichmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_type: Literal[
        "news_report",
        "live_blog",
        "analysis",
        "opinion",
        "editorial",
        "interview",
        "feature",
        "explainer",
        "other",
    ]
    article_type_confidence: float = Field(ge=0.0, le=1.0)
    is_event_coverage: bool = True
    language: str = Field(default="es", min_length=2, max_length=10)
    primary_tag_code: str | None = None
    secondary_tag_codes: list[str] = Field(default_factory=list, max_length=3)
    entities: list[ArticleAnalysisExtractedEntity] = Field(default_factory=list, max_length=12)
    key_phrases: list[str] = Field(default_factory=list, max_length=5)
    claims: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("primary_tag_code")
    @classmethod
    def _validate_primary(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_tag_codes([value])[0]

    @field_validator("secondary_tag_codes")
    @classmethod
    def _validate_secondary(cls, value: list[str]) -> list[str]:
        return validate_tag_codes(value)


class OpenRouterUsage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ArticleAnalysisRead(BaseModel):
    article_id: int
    article_type: str
    article_type_confidence: float
    is_event_coverage: bool
    language: str
    primary_topic_tag_id: int | None = None
    key_phrases_json: str = "[]"
    claims_json: str = "[]"
    extraction_version: str
    content_hash: str
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class StoryClusterMemberReason(BaseModel):
    score: float
    semantic_similarity: float
    title_similarity: float
    shared_entity_score: float
    tag_overlap_score: float
    keyphrase_overlap_score: float
    temporal_proximity_score: float
    days_delta: int = 0
    shared_entity_count: int = 0
    shared_keyphrase_count: int = 0
    shared_tag_count: int = 0
    article_type_pair_class: str = "primary_pair"
    risky_bridge_pair: bool = False
    hard_block: str | None = None
    penalties: list[str] = Field(default_factory=list)


class PairScoreArtifact(BaseModel):
    left_article_id: int
    right_article_id: int
    accepted: bool
    candidate_origins: list[str] = Field(default_factory=list)
    candidate_rank: int | None = None
    reason: StoryClusterMemberReason


class CandidateGenerationSummary(BaseModel):
    seed_article_id: int
    candidate_count: int = 0
    origin_counts: dict[str, int] = Field(default_factory=dict)
    overflow_counts: dict[str, int] = Field(default_factory=dict)


class CandidateRecallSummary(BaseModel):
    positive_pair_count: int
    recall_at_k: dict[str, float] = Field(default_factory=dict)
    covered_pair_count_by_k: dict[str, int] = Field(default_factory=dict)


class ClusterRebuildMetrics(BaseModel):
    article_count: int = 0
    candidate_pair_count: int = 0
    accepted_pair_count: int = 0
    accepted_strong_pair_count: int = 0
    accepted_medium_pair_count: int = 0
    accepted_risky_pair_count: int = 0
    rejected_pair_count: int = 0
    raw_component_count: int = 0
    raw_multi_article_component_count: int = 0
    guarded_cluster_count: int = 0
    guarded_multi_article_cluster_count: int = 0
    cluster_count: int = 0
    singleton_count: int = 0
    attached_singleton_count: int = 0
    unattached_singleton_count: int = 0
    closure_decision_counts: dict[str, int] = Field(default_factory=dict)
    candidate_origin_counts: dict[str, int] = Field(default_factory=dict)
    candidate_overflow_counts: dict[str, int] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class EnrichmentRunMetrics(BaseModel):
    article_count: int = 0
    enriched_count: int = 0
    skipped_count: int = 0
    request_count: int = 0
    invalid_schema_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class EditorialAnalysisRunMetrics(BaseModel):
    article_count: int = 0
    analyzed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    request_count: int = 0
    provider_rejected_count: int = 0
    parse_failed_count: int = 0
    validation_failed_count: int = 0
    strict_success_count: int = 0
    fallback_success_count: int = 0
    fallback_after_strict_reject_count: int = 0
    rows_with_warnings_count: int = 0
    rows_with_truncated_evidence_count: int = 0
    rows_with_dropped_fields_count: int = 0
    rows_with_unmapped_signals_count: int = 0
    unclear_bias_count: int = 0
    unclear_due_to_mapping_count: int = 0
    out_of_domain_count: int = 0
    limited_applicability_count: int = 0
    bias_weak_signal_count: int = 0
    bias_mapping_loss_count: int = 0
    framing_mapping_loss_count: int = 0
    provider_missing_dimension_count: int = 0
    unclear_reason_counts: dict[str, int] = Field(default_factory=dict)
    dimension_status_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    preserved_signal_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
