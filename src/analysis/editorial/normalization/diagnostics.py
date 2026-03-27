from __future__ import annotations

from typing import Any

from src.analysis.editorial.normalization.constants import OUT_OF_DOMAIN_KEYWORDS
from src.analysis.editorial.normalization.types import RepairedEditorialPayload
from src.analysis.shared.contracts import (
    ArticleEditorialAnalysisPayload,
    EditorialAnalysisDiagnostics,
    EditorialDimensionDiagnostic,
)


def build_editorial_diagnostics_from_payload(
    payload: ArticleEditorialAnalysisPayload,
    *,
    provider_path: str = "strict_success",
) -> EditorialAnalysisDiagnostics:
    repaired = RepairedEditorialPayload(
        article_type=payload.article_type,
        article_type_confidence=payload.article_type_confidence,
        bias_label=payload.bias_label,
        ideological_bias_framing=None,
        bias_score=payload.bias_score,
        bias_confidence=payload.bias_confidence,
        confidence=None,
        tone_emotional=payload.tone_emotional,
        tone_target=payload.tone_target,
        opinionatedness=payload.opinionatedness,
        sensationalism=payload.sensationalism,
        rhetorical_certainty=payload.rhetorical_certainty,
        tone_dimensions={},
        framing_devices=list(payload.framing_devices),
        evidence_spans=[item.model_dump(mode="json") for item in payload.evidence_spans],
        rationale=payload.rationale,
        notes=None,
        uncertainty_reason=None,
        repair_warnings=(),
        dropped_fields=(),
        truncated_fields=(),
    )
    applicability, applicability_reason = _classify_applicability(repaired)
    unclear_reasons: set[str] = set()
    if applicability == "out_of_domain":
        unclear_reasons.add("out_of_domain")
    elif applicability == "limited":
        unclear_reasons.add("limited_applicability")

    dimensions = {
        "article_type": _strict_dimension_diagnostic(
            payload.article_type,
            applicability=applicability,
        ),
        "bias": _strict_dimension_diagnostic(
            payload.bias_label,
            applicability=applicability,
        ),
        "tone_emotional": _strict_dimension_diagnostic(
            payload.tone_emotional,
            applicability=applicability,
        ),
        "tone_target": _strict_dimension_diagnostic(
            payload.tone_target,
            applicability=applicability,
        ),
        "opinionatedness": _strict_dimension_diagnostic(
            payload.opinionatedness,
            applicability=applicability,
        ),
        "sensationalism": _strict_dimension_diagnostic(
            payload.sensationalism,
            applicability=applicability,
        ),
        "rhetorical_certainty": _strict_dimension_diagnostic(
            payload.rhetorical_certainty,
            applicability=applicability,
        ),
        "framing": _strict_framing_diagnostic(
            payload.framing_devices,
            applicability=applicability,
        ),
    }
    for diagnostic in dimensions.values():
        if diagnostic.status in {"weak_signal_abstain", "out_of_domain"}:
            unclear_reasons.add(diagnostic.status)

    return EditorialAnalysisDiagnostics(
        provider_path=provider_path,
        editorial_applicability=applicability,
        editorial_applicability_reason=applicability_reason,
        dimension_status=dimensions,
        repair_warnings=[],
        normalization_warnings=[],
        dropped_fields=[],
        truncated_fields=[],
        preserved_signals={},
        provider_failures=[],
        unclear_reasons=sorted(unclear_reasons),
    )


def _classify_applicability(repaired: RepairedEditorialPayload) -> tuple[str, str]:
    joined = " ".join(
        str(x)
        for x in [
            repaired.article_type,
            repaired.rationale,
            repaired.notes,
            repaired.uncertainty_reason,
            repaired.evidence_spans[:3],
        ]
        if x
    ).lower()
    if len(joined.strip()) < 40:
        return "out_of_domain", "insufficient_text"
    for reason, keywords in OUT_OF_DOMAIN_KEYWORDS.items():
        if any(keyword in joined for keyword in keywords):
            return (
                ("limited", "consumer_price_roundup")
                if reason == "consumer_price_roundup"
                else ("out_of_domain", reason)
            )
    if (
        "procedural" in joined
        or "votación" in joined
        or "tribunal" in joined
        or "congreso" in joined
    ):
        return "limited", "procedural_hard_news"
    return "full", "general_editorial_content"


def _diagnose_dimension(
    name: str,
    final_value: str,
    raw_value: Any,
    applicability: str,
    repaired: RepairedEditorialPayload,
    raw_hints: list[str],
) -> EditorialDimensionDiagnostic:
    if applicability == "out_of_domain":
        return EditorialDimensionDiagnostic(
            value=final_value,
            status="out_of_domain",
            reason="content_out_of_domain",
            raw_hints=raw_hints[:12],
        )
    if final_value != "unclear":
        if isinstance(raw_value, str) and any(
            sep in raw_value.lower() for sep in ("/", "mixed", "both")
        ):
            return EditorialDimensionDiagnostic(
                value=final_value,
                status="conflicted_signal",
                reason="raw_signal_was_mixed",
                raw_hints=raw_hints[:12],
            )
        return EditorialDimensionDiagnostic(
            value=final_value,
            status="resolved",
            reason="canonical_value_resolved",
            raw_hints=raw_hints[:12],
        )
    if raw_hints:
        return EditorialDimensionDiagnostic(
            value=final_value,
            status="mapping_loss",
            reason="non_canonical_signal_preserved_in_diagnostics",
            raw_hints=raw_hints[:12],
        )
    if raw_value is None and not repaired.dropped_fields:
        return EditorialDimensionDiagnostic(
            value=final_value,
            status="provider_missing",
            reason="no_raw_value_present",
            raw_hints=raw_hints[:12],
        )
    if repaired.dropped_fields or repaired.truncated_fields:
        return EditorialDimensionDiagnostic(
            value=final_value,
            status="mapping_loss",
            reason="repair_or_mapping_loss_visible",
            raw_hints=raw_hints[:12],
            notes=list(repaired.dropped_fields[:4]),
        )
    if applicability == "limited":
        return EditorialDimensionDiagnostic(
            value=final_value,
            status="weak_signal_abstain",
            reason="limited_editorial_signal",
            raw_hints=raw_hints[:12],
        )
    return EditorialDimensionDiagnostic(
        value=final_value,
        status="weak_signal_abstain",
        reason="honest_abstention",
        raw_hints=raw_hints[:12],
    )


def _diagnose_framing_dimension(
    final_values: list[str],
    unmapped: list[str],
    applicability: str,
    repaired: RepairedEditorialPayload,
) -> EditorialDimensionDiagnostic:
    value = ",".join(final_values) if final_values else "unclear"
    if applicability == "out_of_domain":
        return EditorialDimensionDiagnostic(
            value=value,
            status="out_of_domain",
            reason="content_out_of_domain",
            raw_hints=unmapped[:12],
        )
    if final_values and unmapped:
        return EditorialDimensionDiagnostic(
            value=value,
            status="conflicted_signal",
            reason="resolved_but_partially_lossy",
            raw_hints=unmapped[:12],
        )
    if final_values:
        return EditorialDimensionDiagnostic(
            value=value, status="resolved", reason="canonical_framing_resolved"
        )
    if unmapped or repaired.dropped_fields:
        return EditorialDimensionDiagnostic(
            value="unclear",
            status="mapping_loss",
            reason="framing_taxonomy_dropped_signal",
            raw_hints=unmapped[:12],
        )
    return EditorialDimensionDiagnostic(
        value="unclear", status="weak_signal_abstain", reason="no_stable_framing_signal"
    )


def _strict_dimension_diagnostic(
    value: str,
    *,
    applicability: str,
) -> EditorialDimensionDiagnostic:
    if applicability == "out_of_domain":
        return EditorialDimensionDiagnostic(
            value=value,
            status="out_of_domain",
            reason="content_out_of_domain",
        )
    if value != "unclear":
        return EditorialDimensionDiagnostic(
            value=value,
            status="resolved",
            reason="canonical_value_resolved",
        )
    return EditorialDimensionDiagnostic(
        value=value,
        status="weak_signal_abstain",
        reason=(
            "limited_editorial_signal"
            if applicability == "limited"
            else "honest_abstention"
        ),
    )


def _strict_framing_diagnostic(
    values: list[str],
    *,
    applicability: str,
) -> EditorialDimensionDiagnostic:
    value = ",".join(values) if values else "unclear"
    if applicability == "out_of_domain":
        return EditorialDimensionDiagnostic(
            value=value,
            status="out_of_domain",
            reason="content_out_of_domain",
        )
    if values:
        return EditorialDimensionDiagnostic(
            value=value,
            status="resolved",
            reason="canonical_framing_resolved",
        )
    return EditorialDimensionDiagnostic(
        value="unclear",
        status="weak_signal_abstain",
        reason=(
            "limited_editorial_signal"
            if applicability == "limited"
            else "no_stable_framing_signal"
        ),
    )
