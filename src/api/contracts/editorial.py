from __future__ import annotations

from pydantic import BaseModel, Field


class EditorialEvidenceSpan(BaseModel):
    type: str
    text: str
    note: str


class EditorialReviewFlags(BaseModel):
    missing_evidence: bool = False
    low_confidence: bool = False
    failed_analysis: bool = False
    unclear_bias: bool = False
    provider_missing: bool = False
    mapping_loss: bool = False
    out_of_domain: bool = False
    pending_analysis: bool = False
    needs_review: bool = False


class EditorialDiagnostics(BaseModel):
    provider_path: str = ""
    editorial_applicability: str = "full"
    editorial_applicability_reason: str = "general_editorial_content"
    dimension_status: dict = Field(default_factory=dict)
    repair_warnings: list[str] = Field(default_factory=list)
    normalization_warnings: list[str] = Field(default_factory=list)
    dropped_fields: list[str] = Field(default_factory=list)
    truncated_fields: list[str] = Field(default_factory=list)
    preserved_signals: dict = Field(default_factory=dict)
    provider_failures: list[str] = Field(default_factory=list)
    unclear_reasons: list[str] = Field(default_factory=list)


class ArticleEditorialAnalysisListItem(BaseModel):
    article_id: int
    source: str
    section: str = ""
    title: str
    url: str
    published_at: str | None = None
    summary: str = ""
    article_type: str = "unclear"
    article_type_confidence: float = 0.0
    editorial_applicability: str = "full"
    provider_failure_class: str = ""
    analysis_path: str = ""
    unclear_reasons: list[str] = Field(default_factory=list)
    article_type_status: str = ""
    bias_status: str = ""
    tone_emotional_status: str = ""
    opinionatedness_status: str = ""
    framing_status: str = ""
    bias_label: str = "unclear"
    bias_score: float = 0.0
    bias_confidence: float = 0.0
    tone_emotional: str = "unclear"
    opinionatedness: str = "unclear"
    analysis_status: str
    rationale: str = ""
    evidence_count: int = 0
    evidence_spans: list[EditorialEvidenceSpan] = Field(default_factory=list)
    failure_reason: str = ""
    analyzed_at: str | None = None
    review_flags: EditorialReviewFlags = Field(default_factory=EditorialReviewFlags)


class ArticleEditorialAnalysisListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ArticleEditorialAnalysisListItem] = Field(default_factory=list)


class ArticleEditorialAnalysisResponse(BaseModel):
    article_id: int
    source: str
    section: str = ""
    title: str
    url: str
    published_at: str | None = None
    summary: str = ""
    content_preview: str = ""
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
    unclear_reasons: list[str] = Field(default_factory=list)
    article_type_status: str = ""
    bias_status: str = ""
    tone_emotional_status: str = ""
    tone_target_status: str = ""
    opinionatedness_status: str = ""
    sensationalism_status: str = ""
    rhetorical_certainty_status: str = ""
    framing_status: str = ""
    framing_devices: list[str] = Field(default_factory=list)
    evidence_spans: list[EditorialEvidenceSpan] = Field(default_factory=list)
    diagnostics: EditorialDiagnostics = Field(default_factory=EditorialDiagnostics)
    rationale: str
    analysis_status: str
    failure_reason: str = ""
    model_provider: str
    model_name: str
    model_version: str = ""
    prompt_version: str
    schema_version: str
    content_hash: str
    source_text_version: str
    analyzed_at: str | None = None
    updated_at: str | None = None
    review_flags: EditorialReviewFlags = Field(default_factory=EditorialReviewFlags)
