from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.analysis.shared.contracts import (
    ArticleEditorialAnalysisPayload,
    ArticleEditorialAnalysisRawPayload,
    EditorialAnalysisDiagnostics,
)


@dataclass(frozen=True)
class RepairedEditorialPayload:
    article_type: Any
    article_type_confidence: float | None
    bias_label: Any
    ideological_bias_framing: Any
    bias_score: float | None
    bias_confidence: float | None
    confidence: float | None
    tone_emotional: Any
    tone_target: Any
    opinionatedness: Any
    sensationalism: Any
    rhetorical_certainty: Any
    tone_dimensions: dict[str, Any]
    framing_devices: list[Any]
    evidence_spans: list[Any]
    rationale: str | None
    notes: str | None
    uncertainty_reason: str | None
    repair_warnings: tuple[str, ...]
    dropped_fields: tuple[str, ...]
    truncated_fields: tuple[str, ...]


@dataclass(frozen=True)
class EditorialNormalizationResult:
    raw_payload: ArticleEditorialAnalysisRawPayload
    repaired_payload: RepairedEditorialPayload
    final_payload: ArticleEditorialAnalysisPayload
    diagnostics: EditorialAnalysisDiagnostics
    warnings: tuple[str, ...]
    repair_warnings: tuple[str, ...]
    normalization_warnings: tuple[str, ...]
    dropped_fields: tuple[str, ...]
    truncated_fields: tuple[str, ...]
    unclear_reasons: tuple[str, ...]


@dataclass(frozen=True)
class EditorialNormalizationError(Exception):
    message: str
    raw_payload: ArticleEditorialAnalysisRawPayload | None = None
    warnings: tuple[str, ...] = ()
    repair_warnings: tuple[str, ...] = ()
    normalization_warnings: tuple[str, ...] = ()
    dropped_fields: tuple[str, ...] = ()
    truncated_fields: tuple[str, ...] = ()
    unclear_reasons: tuple[str, ...] = ()

    def __str__(self) -> str:
        return self.message
