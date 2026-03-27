from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.analysis.editorial.normalization.constants import (
    ARTICLE_TYPE_ALIASES,
    BIAS_LABEL_ALIASES,
    OPINIONATEDNESS_ALIASES,
    RHETORICAL_CERTAINTY_ALIASES,
    SENSATIONALISM_ALIASES,
    TONE_EMOTIONAL_ALIASES,
    TONE_TARGET_ALIASES,
)
from src.analysis.editorial.normalization.diagnostics import (
    _classify_applicability,
    _diagnose_dimension,
    _diagnose_framing_dimension,
)
from src.analysis.editorial.normalization.repair import (
    _collect_tone_hints,
    _extract_bias_hints,
    _extract_bias_label,
    _normalize_choice,
    _normalize_evidence_spans,
    _normalize_framing_devices,
    _normalize_rationale,
    _resolve_bias_score,
    _resolve_confidence,
    _resolve_opinionatedness_source,
    _resolve_rhetorical_certainty_source,
    _resolve_sensationalism_source,
    _resolve_tone_emotional_source,
    _resolve_tone_target_source,
    repair_editorial_raw_payload,
)
from src.analysis.editorial.normalization.types import (
    EditorialNormalizationError,
    EditorialNormalizationResult,
)
from src.analysis.shared.contracts import (
    ARTICLE_TYPES,
    BIAS_LABELS,
    OPINIONATEDNESS_VALUES,
    RHETORICAL_CERTAINTY_VALUES,
    SENSATIONALISM_VALUES,
    TONE_EMOTIONAL_VALUES,
    TONE_TARGET_VALUES,
    ArticleEditorialAnalysisPayload,
    ArticleEditorialAnalysisRawPayload,
    EditorialAnalysisDiagnostics,
)


def normalize_editorial_payload(raw_payload: dict[str, Any]) -> EditorialNormalizationResult:
    try:
        raw = ArticleEditorialAnalysisRawPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise EditorialNormalizationError(f"raw payload validation failed: {exc}") from exc

    repaired = repair_editorial_raw_payload(raw)
    normalization_warnings: list[str] = []
    unclear_reasons: set[str] = set()
    preserved_signals: dict[str, list[str]] = {}

    applicability, applicability_reason = _classify_applicability(repaired)
    if applicability != "full":
        unclear_reasons.add(
            "out_of_domain" if applicability == "out_of_domain" else "limited_applicability"
        )

    article_type = _normalize_choice(
        repaired.article_type,
        allowed=set(ARTICLE_TYPES) | {"unclear"},
        aliases=ARTICLE_TYPE_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="article_type",
    )
    article_type_confidence = _resolve_confidence(
        repaired.article_type_confidence,
        repaired.confidence,
        0.3 if article_type == "unclear" else 0.55,
        0.6 if article_type == "unclear" else None,
    )

    raw_bias_label = repaired.bias_label or _extract_bias_label(repaired.ideological_bias_framing)
    bias_label = _normalize_choice(
        raw_bias_label,
        allowed=set(BIAS_LABELS),
        aliases=BIAS_LABEL_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="bias_label",
    )
    if bias_label == "unclear" and (
        raw_bias_label is None
        or str(raw_bias_label).strip().lower() in {"unclear", "neutral", "none"}
    ):
        unclear_reasons.add("semantic_weak_signal")
    bias_score = _resolve_bias_score(repaired.bias_score, bias_label)
    bias_confidence = _resolve_confidence(
        repaired.bias_confidence,
        repaired.confidence,
        0.3 if bias_label == "unclear" else 0.5,
        0.6 if bias_label == "unclear" else None,
    )

    tone_dimensions = repaired.tone_dimensions or {}
    tone_emotional_source = _resolve_tone_emotional_source(repaired, tone_dimensions)
    tone_emotional = _normalize_choice(
        tone_emotional_source,
        allowed=set(TONE_EMOTIONAL_VALUES),
        aliases=TONE_EMOTIONAL_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="tone_emotional",
    )
    tone_target_source = _resolve_tone_target_source(repaired, tone_dimensions)
    tone_target = _normalize_choice(
        tone_target_source,
        allowed=set(TONE_TARGET_VALUES),
        aliases=TONE_TARGET_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="tone_target",
    )
    opinionatedness_source = _resolve_opinionatedness_source(repaired, tone_dimensions)
    opinionatedness = _normalize_choice(
        opinionatedness_source,
        allowed=set(OPINIONATEDNESS_VALUES),
        aliases=OPINIONATEDNESS_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="opinionatedness",
    )
    sensationalism_source = _resolve_sensationalism_source(repaired, tone_dimensions)
    sensationalism = _normalize_choice(
        sensationalism_source,
        allowed=set(SENSATIONALISM_VALUES),
        aliases=SENSATIONALISM_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="sensationalism",
    )
    rhetorical_certainty_source = _resolve_rhetorical_certainty_source(repaired, tone_dimensions)
    rhetorical_certainty = _normalize_choice(
        rhetorical_certainty_source,
        allowed=set(RHETORICAL_CERTAINTY_VALUES),
        aliases=RHETORICAL_CERTAINTY_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="rhetorical_certainty",
    )

    framing_devices, unmapped_framing = _normalize_framing_devices(
        repaired.framing_devices, normalization_warnings
    )
    if unmapped_framing:
        preserved_signals["framing_candidates"] = unmapped_framing
    evidence_spans = _normalize_evidence_spans(repaired.evidence_spans, normalization_warnings)
    rationale = _normalize_rationale(repaired, normalization_warnings)

    tone_hints = _collect_tone_hints(repaired, tone_dimensions)
    if tone_hints:
        preserved_signals["tone_hints"] = tone_hints
    notes_hints = [
        text
        for text in (repaired.notes, repaired.uncertainty_reason)
        if isinstance(text, str) and text.strip()
    ]
    if notes_hints:
        preserved_signals["notes_hints"] = notes_hints[:4]

    if repaired.dropped_fields or repaired.truncated_fields:
        unclear_reasons.add("repair_data_loss")

    dimensions = {
        "article_type": _diagnose_dimension(
            "article_type",
            article_type,
            repaired.article_type,
            applicability,
            repaired,
            raw_hints=[],
        ),
        "bias": _diagnose_dimension(
            "bias",
            bias_label,
            raw_bias_label,
            applicability,
            repaired,
            raw_hints=_extract_bias_hints(repaired),
        ),
        "tone_emotional": _diagnose_dimension(
            "tone_emotional",
            tone_emotional,
            tone_emotional_source,
            applicability,
            repaired,
            raw_hints=tone_hints,
        ),
        "tone_target": _diagnose_dimension(
            "tone_target",
            tone_target,
            tone_target_source,
            applicability,
            repaired,
            raw_hints=tone_hints,
        ),
        "opinionatedness": _diagnose_dimension(
            "opinionatedness",
            opinionatedness,
            opinionatedness_source,
            applicability,
            repaired,
            raw_hints=tone_hints,
        ),
        "sensationalism": _diagnose_dimension(
            "sensationalism",
            sensationalism,
            sensationalism_source,
            applicability,
            repaired,
            raw_hints=tone_hints,
        ),
        "rhetorical_certainty": _diagnose_dimension(
            "rhetorical_certainty",
            rhetorical_certainty,
            rhetorical_certainty_source,
            applicability,
            repaired,
            raw_hints=tone_hints,
        ),
        "framing": _diagnose_framing_dimension(
            framing_devices, unmapped_framing, applicability, repaired
        ),
    }

    for diag in dimensions.values():
        if diag.status in {
            "mapping_loss",
            "provider_missing",
            "weak_signal_abstain",
            "out_of_domain",
        }:
            unclear_reasons.add(diag.status)

    try:
        final_payload = ArticleEditorialAnalysisPayload.model_validate(
            {
                "article_type": article_type,
                "article_type_confidence": article_type_confidence,
                "bias_label": bias_label,
                "bias_score": bias_score,
                "bias_confidence": bias_confidence,
                "tone_emotional": tone_emotional,
                "tone_target": tone_target,
                "opinionatedness": opinionatedness,
                "sensationalism": sensationalism,
                "rhetorical_certainty": rhetorical_certainty,
                "framing_devices": framing_devices,
                "evidence_spans": evidence_spans,
                "rationale": rationale,
            }
        )
    except ValidationError as exc:
        raise EditorialNormalizationError(
            f"final payload validation failed after normalization: {exc}",
            raw_payload=raw,
            warnings=tuple([*repaired.repair_warnings, *normalization_warnings]),
            repair_warnings=repaired.repair_warnings,
            normalization_warnings=tuple(normalization_warnings),
            dropped_fields=repaired.dropped_fields,
            truncated_fields=repaired.truncated_fields,
            unclear_reasons=tuple(sorted(unclear_reasons)),
        ) from exc

    diagnostics = EditorialAnalysisDiagnostics(
        provider_path="normalized_local_pipeline",
        editorial_applicability=applicability,
        editorial_applicability_reason=applicability_reason,
        dimension_status=dimensions,
        repair_warnings=list(repaired.repair_warnings),
        normalization_warnings=normalization_warnings,
        dropped_fields=list(repaired.dropped_fields),
        truncated_fields=list(repaired.truncated_fields),
        preserved_signals=preserved_signals,
        provider_failures=[],
        unclear_reasons=sorted(unclear_reasons),
    )
    return EditorialNormalizationResult(
        raw_payload=raw,
        repaired_payload=repaired,
        final_payload=final_payload,
        diagnostics=diagnostics,
        warnings=tuple([*repaired.repair_warnings, *normalization_warnings]),
        repair_warnings=repaired.repair_warnings,
        normalization_warnings=tuple(normalization_warnings),
        dropped_fields=repaired.dropped_fields,
        truncated_fields=repaired.truncated_fields,
        unclear_reasons=tuple(sorted(unclear_reasons)),
    )
