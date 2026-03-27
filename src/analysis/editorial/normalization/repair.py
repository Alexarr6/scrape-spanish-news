from __future__ import annotations

from src.analysis.editorial.normalization.repair_parts import (
    coercion,
    inference,
    payload_normalization,
)
from src.analysis.editorial.normalization.types import RepairedEditorialPayload
from src.analysis.shared.contracts import ArticleEditorialAnalysisRawPayload

_collect_tone_hints = inference.collect_tone_hints
_extract_bias_hints = inference.extract_bias_hints
_resolve_opinionatedness_source = inference.resolve_opinionatedness_source
_resolve_rhetorical_certainty_source = inference.resolve_rhetorical_certainty_source
_resolve_sensationalism_source = inference.resolve_sensationalism_source
_resolve_tone_emotional_source = inference.resolve_tone_emotional_source
_resolve_tone_target_source = inference.resolve_tone_target_source

_extract_bias_label = coercion.extract_bias_label
_repair_bias_score = coercion.repair_bias_score
_repair_confidence = coercion.repair_confidence
_repair_evidence_spans = coercion.repair_evidence_spans
_repair_framing_devices = coercion.repair_framing_devices
_repair_text_like = coercion.repair_text_like
_repair_tone_dimensions = coercion.repair_tone_dimensions

_normalize_choice = payload_normalization.normalize_choice
_normalize_evidence_spans = payload_normalization.normalize_evidence_spans
_normalize_framing_devices = payload_normalization.normalize_framing_devices
_normalize_rationale = payload_normalization.normalize_rationale
_resolve_bias_score = payload_normalization.resolve_bias_score
_resolve_confidence = payload_normalization.resolve_confidence


def repair_editorial_raw_payload(
    raw: ArticleEditorialAnalysisRawPayload,
) -> RepairedEditorialPayload:
    repair_warnings: list[str] = []
    dropped_fields: list[str] = []
    truncated_fields: list[str] = []
    confidence = _repair_confidence(raw.confidence, "confidence", repair_warnings, dropped_fields)
    article_type_confidence = _repair_confidence(
        raw.article_type_confidence, "article_type_confidence", repair_warnings, dropped_fields
    )
    bias_confidence = _repair_confidence(
        raw.bias_confidence, "bias_confidence", repair_warnings, dropped_fields
    )
    rationale = _repair_text_like(
        raw.rationale,
        field_name="rationale",
        object_keys=("summary", "description", "rationale", "justification", "framing_summary"),
        repair_warnings=repair_warnings,
        dropped_fields=dropped_fields,
        min_length=12,
    )
    notes = _repair_text_like(
        raw.notes,
        field_name="notes",
        object_keys=("summary", "description", "note", "classification_notes", "source_treatment"),
        repair_warnings=repair_warnings,
        dropped_fields=dropped_fields,
        min_length=3,
    )
    uncertainty_reason = _repair_text_like(
        raw.uncertainty_reason,
        field_name="uncertainty_reason",
        object_keys=("summary", "description", "reason"),
        repair_warnings=repair_warnings,
        dropped_fields=dropped_fields,
        min_length=3,
    )
    ideological_bias_framing = raw.ideological_bias_framing
    if isinstance(ideological_bias_framing, dict):
        nested_confidence = _repair_confidence(
            ideological_bias_framing.get("confidence"),
            "ideological_bias_framing.confidence",
            repair_warnings,
            dropped_fields,
        )
        if bias_confidence is None and nested_confidence is not None:
            bias_confidence = nested_confidence
            repair_warnings.append(
                "repair_promoted_confidence: ideological_bias_framing.confidence -> bias_confidence"
            )
    tone_dimensions = _repair_tone_dimensions(raw.tone_dimensions, repair_warnings)
    framing_devices = _repair_framing_devices(
        raw.framing_devices, repair_warnings, dropped_fields, truncated_fields
    )
    evidence_spans = _repair_evidence_spans(
        raw.evidence_spans, repair_warnings, dropped_fields, truncated_fields
    )
    return RepairedEditorialPayload(
        article_type=raw.article_type,
        article_type_confidence=article_type_confidence,
        bias_label=raw.bias_label,
        ideological_bias_framing=ideological_bias_framing,
        bias_score=_repair_bias_score(raw.bias_score, repair_warnings, dropped_fields),
        bias_confidence=bias_confidence,
        confidence=confidence,
        tone_emotional=raw.tone_emotional,
        tone_target=raw.tone_target,
        opinionatedness=raw.opinionatedness,
        sensationalism=raw.sensationalism,
        rhetorical_certainty=raw.rhetorical_certainty,
        tone_dimensions=tone_dimensions,
        framing_devices=framing_devices,
        evidence_spans=evidence_spans,
        rationale=rationale,
        notes=notes,
        uncertainty_reason=uncertainty_reason,
        repair_warnings=tuple(repair_warnings),
        dropped_fields=tuple(dropped_fields),
        truncated_fields=tuple(truncated_fields),
    )
