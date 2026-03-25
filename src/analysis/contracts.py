from __future__ import annotations

from datetime import date, datetime
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
from src.analysis.taxonomy import validate_tag_codes

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
ENTITY_TYPES = (
    "politician",
    "political_party",
    "person",
    "organization",
    "institution",
    "country",
    "region_city",
    "company",
    "event",
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


class ArticleEditorialAnalysisRead(BaseModel):
    article_id: int
    article_type: str
    article_type_confidence: float
    bias_label: str
    bias_score: float
    bias_confidence: float
    tone_emotional: str
    tone_target: str
    opinionatedness: str
    sensationalism: str
    rhetorical_certainty: str
    editorial_applicability: str = "full"
    editorial_applicability_reason: str = "general_editorial_content"
    provider_failure_class: str = ""
    analysis_path: str = ""
    unclear_reasons_json: str = "[]"
    article_type_status: str = ""
    bias_status: str = ""
    tone_emotional_status: str = ""
    tone_target_status: str = ""
    opinionatedness_status: str = ""
    sensationalism_status: str = ""
    rhetorical_certainty_status: str = ""
    framing_status: str = ""
    framing_devices_json: str = "[]"
    evidence_spans_json: str = "[]"
    diagnostics_json: str = "{}"
    rationale: str
    analysis_status: str
    failure_reason: str = ""
    model_provider: str
    model_name: str
    model_version: str = ""
    prompt_version: str
    schema_version: str
    content_hash: str
    source_text_version: str = "title_summary_body_v1"
    analyzed_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EntityRead(BaseModel):
    id: int
    entity_type: str
    canonical_name: str
    normalized_name: str
    slug: str
    canonical_source: str

    model_config = ConfigDict(from_attributes=True)


class EntityMentionRead(BaseModel):
    id: int
    article_id: int
    entity_id: int
    surface_form: str
    mention_text_normalized: str
    mention_count: int
    title_hits: int
    summary_hits: int
    body_hits: int
    relevance_score: float
    role_hint: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TagRead(BaseModel):
    id: int
    tag_code: str
    display_name: str
    tag_group: str
    description: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class StoryClusterRead(BaseModel):
    id: int
    cluster_key: str
    status: str
    cluster_type: str
    summary_headline: str
    summary_text: str
    article_count: int
    source_count: int
    clustering_version: str

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
    rejected_pair_count: int = 0
    cluster_count: int = 0
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


class StoryClusterQuery(BaseModel):
    days_back: int | None = Field(default=None, ge=1)
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=100, ge=1, le=1000)
