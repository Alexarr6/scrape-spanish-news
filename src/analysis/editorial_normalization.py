from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from src.analysis.contracts import (
    ARTICLE_TYPES,
    BIAS_LABELS,
    EVIDENCE_SPAN_TYPES,
    FRAMING_DEVICE_VALUES,
    OPINIONATEDNESS_VALUES,
    RHETORICAL_CERTAINTY_VALUES,
    SENSATIONALISM_VALUES,
    TONE_EMOTIONAL_VALUES,
    TONE_TARGET_VALUES,
    ArticleEditorialAnalysisPayload,
    ArticleEditorialAnalysisRawPayload,
    EditorialAnalysisDiagnostics,
    EditorialDimensionDiagnostic,
)

ARTICLE_TYPE_ALIASES = {
    "breaking_news": "news_report",
    "breaking_news_crime_report": "news_report",
    "crime_report": "news_report",
    "crime_news": "news_report",
    "noticia_accidente": "news_report",
    "straight_news": "news_report",
    "straight_reporting": "news_report",
    "news": "news_report",
    "report": "news_report",
    "match_report": "news_report",
    "election_results_report": "news_report",
    "local_news_event_coverage": "news_report",
    "analysis_piece": "analysis",
    "op_ed": "opinion",
    "op-ed": "opinion",
    "column": "opinion",
    "qa": "interview",
    "q&a": "interview",
    "longform_feature": "feature",
    "long_form_feature": "feature",
    "backgrounder": "explainer",
}
BIAS_LABEL_ALIASES = {
    "far-left": "far_left",
    "center-left": "center_left",
    "centre-left": "center_left",
    "centre": "center",
    "centered": "center",
    "center-right": "center_right",
    "centre-right": "center_right",
    "far-right": "far_right",
    "neutral": "unclear",
    "none": "unclear",
    "no_bias": "unclear",
    "non_ideological": "unclear",
    "sin_sesgo_claro": "unclear",
    "pro_real_madrid": "unclear",
    "protester_sympathetic": "unclear",
}
TONE_EMOTIONAL_ALIASES = {
    "neutral": "calm",
    "objective": "calm",
    "restrained": "calm",
    "descriptive": "calm",
    "factual": "calm",
    "measured": "calm",
    "informative_and_sober": "calm",
    "informativo_y_sobrio": "calm",
    "low": "calm",
    "baja": "calm",
    "bajo": "calm",
    "false": "calm",
    "moderate": "loaded",
    "medium": "loaded",
    "high": "loaded",
    "very_high": "inflammatory",
    "emotional": "loaded",
    "charged": "loaded",
    "alarmist": "inflammatory",
    "provocative": "inflammatory",
    "none": "calm",
}
TONE_TARGET_ALIASES = {
    "balanced": "mixed",
    "ambivalent": "mixed",
    "negative": "critical",
    "adversarial": "hostile",
    "positive": "supportive",
    "objective": "neutral",
    "none": "neutral",
    "partial": "mixed",
    "false": "neutral",
}
OPINIONATEDNESS_ALIASES = {
    "objective_reporting": "straight_reporting",
    "factual_reporting": "straight_reporting",
    "news_reporting": "straight_reporting",
    "analysis": "interpretive",
    "commentary": "opinionated",
    "advocacy": "activist",
    "neutral": "straight_reporting",
    "absent": "opinionated",
    "high": "opinionated",
    "moderate": "interpretive",
    "low": "straight_reporting",
    "false": "straight_reporting",
}
SENSATIONALISM_ALIASES = {
    "none": "low",
    "minimal": "low",
    "low": "low",
    "bajo": "low",
    "baja": "low",
    "moderate": "medium",
    "media": "medium",
    "medio": "medium",
    "elevated": "medium",
    "very_high": "high",
    "alta": "high",
    "alto": "high",
    "false": "low",
    "true": "medium",
}
RHETORICAL_CERTAINTY_ALIASES = {
    "measured": "cautious",
    "qualified": "cautious",
    "neutral": "assertive",
    "factual": "assertive",
    "direct": "assertive",
    "categorical": "absolute",
    "dogmatic": "absolute",
    "high": "assertive",
    "moderate": "assertive",
    "low": "cautious",
}
FRAMING_DEVICE_ALIASES = {
    "security": "public_order_security",
    "law_and_order": "public_order_security",
    "public_safety": "public_order_security",
    "crime_public_safety": "public_order_security",
    "order_and_security": "public_order_security",
    "geopolitics": "strategic_geopolitics",
    "strategic_security": "strategic_geopolitics",
    "stability": "institutional_stability",
    "institutional_continuity": "institutional_stability",
    "anti_corruption": "corruption_scandal",
    "corruption": "corruption_scandal",
    "victim_frame": "victimization",
    "human_rights": "humanitarian",
    "culture_war": "identity_culture",
    "economic_impact": "economic_consequence",
    "competence": "governance_competence",
    "conflict_frame": "conflict",
    "moral_frame": "moral_judgment",
    "modernization": "progress_modernization",
    "martial_warfare": "conflict",
    "crisis_framing": "conflict",
    "binary_framing": "conflict",
    "headline_ambiguity": "conflict",
    "religious_sacramental": "moral_judgment",
    "heroic_narrative": "victimization",
    "epic_heroic": "victimization",
    "heroes_victims": "victimization",
    "regional_pride": "identity_culture",
    "movement_legitimacy_language": "identity_culture",
    "impact_amplification": "economic_consequence",
    "quantitative_acceleration": "economic_consequence",
    "scope_expansion": "institutional_stability",
    "growth_framing": "conflict",
    "collective_action": "conflict",
    "grassroots_legitimacy": "identity_culture",
    "rural_urban_tension": "identity_culture",
    "preventive_advocacy": "moral_judgment",
    "accusatory_headline": "conflict",
    "no_counterbalance": "conflict",
    "procedural_focus": "institutional_stability",
    "direct_quote": "institutional_stability",
    "single_source": "institutional_stability",
    "direct_quotation_of_critical_questions": "conflict",
    "opposition_questions_as_headline_focus": "conflict",
    "multiple_party_coverage_for_balance": "institutional_stability",
    "temporal_framing_emphasizing_finality": "institutional_stability",
}
CONFIDENCE_LABEL_ALIASES = {
    "low": 0.25,
    "bajo": 0.25,
    "baja": 0.25,
    "moderate": 0.5,
    "medium": 0.5,
    "medio": 0.5,
    "media": 0.5,
    "high": 0.75,
    "alto": 0.75,
    "alta": 0.75,
}
RAW_EVIDENCE_WORKING_CAP = 6
RAW_FRAMING_WORKING_CAP = 12


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


BIAS_SCORE_BY_LABEL = {
    "far_left": -0.9,
    "left": -0.65,
    "center_left": -0.35,
    "center": 0.0,
    "center_right": 0.35,
    "right": 0.65,
    "far_right": 0.9,
    "unclear": 0.0,
}
OUT_OF_DOMAIN_KEYWORDS = {
    "sports_recap": ("liga", "gol", "partido", "entrenador", "victoria", "derrota", "champions"),
    "accident_crime_bulletin": (
        "accidente",
        "herido",
        "muerto",
        "emergencias",
        "suceso",
        "arma blanca",
        "tráfico",
    ),
    "consumer_price_roundup": (
        "precio",
        "euros",
        "ofertas",
        "hoteles",
        "viajar",
        "gasolina",
        "supermercado",
    ),
    "weather_or_service_info": (
        "temperaturas",
        "lluvia",
        "tráfico",
        "cortes",
        "aviso amarillo",
        "servicio",
    ),
}


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


def _extract_bias_hints(repaired: RepairedEditorialPayload) -> list[str]:
    hints: list[str] = []
    value = repaired.ideological_bias_framing
    if isinstance(value, str) and value.strip():
        hints.append(value.strip())
    elif isinstance(value, dict):
        for key in (
            "position",
            "orientation",
            "description",
            "evidence",
            "justification",
            "notes",
            "framing_summary",
            "source_treatment",
            "classification_notes",
        ):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                hints.append(f"{key}={candidate.strip()}")
    return hints[:12]


def _collect_tone_hints(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> list[str]:
    hints: list[str] = []
    for key, value in tone_dimensions.items():
        if key in {
            "emotionality",
            "emotional_valence",
            "target",
            "polarity",
            "opinionatedness",
            "style",
            "sensationalism",
            "alarmism",
            "rhetorical_certainty",
            "certainty",
        }:
            continue
        if isinstance(value, dict):
            inner = (
                value.get("description")
                or value.get("label")
                or value.get("value")
                or value.get("level")
            )
            if isinstance(inner, str) and inner.strip():
                hints.append(f"{key}={inner.strip()}")
        elif isinstance(value, str) and value.strip():
            hints.append(f"{key}={value.strip()}")
    for item in (repaired.notes, repaired.uncertainty_reason):
        if isinstance(item, str) and item.strip():
            hints.append(item.strip())
    return hints[:12]


def _resolve_tone_emotional_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.tone_emotional
        or _extract_nested_choice(tone_dimensions, "emotionality")
        or _extract_nested_choice(tone_dimensions, "emotional_valence")
        or _extract_nested_choice(tone_dimensions, "overall_tone")
        or _extract_nested_choice(tone_dimensions, "overall")
        or _extract_nested_choice(tone_dimensions, "emotional_tone")
        or _extract_nested_choice(tone_dimensions, "emotional_charge")
        or _extract_nested_choice(tone_dimensions, "dramatic")
        or _extract_nested_choice(tone_dimensions, "sentiment")
        or _infer_tone_emotional_from_hints(tone_dimensions)
    )


def _resolve_tone_target_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.tone_target
        or _extract_nested_choice(tone_dimensions, "target")
        or _extract_nested_choice(tone_dimensions, "polarity")
        or _extract_nested_choice(tone_dimensions, "government_assessment")
        or _extract_nested_choice(tone_dimensions, "sentiment")
        or _infer_tone_target_from_hints(tone_dimensions)
    )


def _resolve_opinionatedness_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.opinionatedness
        or _extract_nested_choice(tone_dimensions, "opinionatedness")
        or _extract_nested_choice(tone_dimensions, "style")
        or _extract_nested_choice(tone_dimensions, "neutral_reporting")
        or _extract_nested_choice(tone_dimensions, "partisan")
        or _extract_nested_choice(tone_dimensions, "subjectivity")
        or _extract_nested_choice(tone_dimensions, "analytical")
        or _extract_nested_choice(tone_dimensions, "informational_balance")
        or _infer_opinionatedness_from_hints(tone_dimensions)
    )


def _resolve_sensationalism_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.sensationalism
        or _extract_nested_choice(tone_dimensions, "sensationalism")
        or _extract_nested_choice(tone_dimensions, "alarmism")
        or _extract_nested_choice(tone_dimensions, "loaded_language")
        or _infer_sensationalism_from_hints(tone_dimensions)
    )


def _resolve_rhetorical_certainty_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.rhetorical_certainty
        or _extract_nested_choice(tone_dimensions, "rhetorical_certainty")
        or _extract_nested_choice(tone_dimensions, "certainty")
        or _extract_nested_choice(tone_dimensions, "confidence")
        or _infer_rhetorical_certainty_from_hints(tone_dimensions)
    )


def _infer_tone_emotional_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    accusatory = _hint_strength(tone_dimensions, "accusatory")
    critical = _hint_strength(tone_dimensions, "critical")
    partisanship = _hint_strength(tone_dimensions, "partisancy", "partisan")
    procedural = _hint_strength(tone_dimensions, "procedural")
    conflict = _hint_strength(tone_dimensions, "conflict_framing")

    if max(accusatory, critical, partisanship, conflict) >= 3:
        return "inflammatory"
    if max(accusatory, critical, partisanship, conflict) >= 2:
        return "loaded"
    if procedural >= 2:
        return "calm"
    return None


def _infer_tone_target_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    accusatory = _hint_strength(tone_dimensions, "accusatory")
    critical = _hint_strength(tone_dimensions, "critical")
    accountability = _extract_hint_text(tone_dimensions, "accountability_attribution")
    mobilization = _extract_hint_text(tone_dimensions, "mobilization_framing")
    procedural = _hint_strength(tone_dimensions, "procedural")

    if accusatory >= 3:
        return "hostile"
    if max(accusatory, critical) >= 2:
        return "critical"
    if accountability and accountability not in {"none", "neutral", "mixed"}:
        return "critical"
    if mobilization and "positive" in mobilization:
        return "supportive"
    if procedural >= 2:
        return "neutral"
    return None


def _infer_opinionatedness_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    partisanship = _hint_strength(tone_dimensions, "partisancy", "partisan")
    accusatory = _hint_strength(tone_dimensions, "accusatory")
    critical = _hint_strength(tone_dimensions, "critical")
    mobilization = _extract_hint_text(tone_dimensions, "mobilization_framing")
    procedural = _hint_strength(tone_dimensions, "procedural")

    if mobilization and any(token in mobilization for token in ("legitimizing", "advocacy")):
        return "activist"
    if partisanship >= 2 or max(accusatory, critical) >= 3:
        return "opinionated"
    if max(accusatory, critical) >= 2:
        return "interpretive"
    if procedural >= 2:
        return "straight_reporting"
    return None


def _infer_sensationalism_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    accusatory = _hint_strength(tone_dimensions, "accusatory")
    critical = _hint_strength(tone_dimensions, "critical")
    conflict = _hint_strength(tone_dimensions, "conflict_framing")
    procedural = _hint_strength(tone_dimensions, "procedural")

    if max(accusatory, critical, conflict) >= 3:
        return "high"
    if max(accusatory, critical, conflict) >= 2:
        return "medium"
    if procedural >= 2:
        return "low"
    return None


def _infer_rhetorical_certainty_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    accusatory = _hint_strength(tone_dimensions, "accusatory")
    critical = _hint_strength(tone_dimensions, "critical")
    procedural = _hint_strength(tone_dimensions, "procedural")

    if max(accusatory, critical) >= 3:
        return "absolute"
    if max(accusatory, critical) >= 2:
        return "assertive"
    if procedural >= 2:
        return "cautious"
    return None


def _extract_hint_text(tone_dimensions: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _extract_nested_choice(tone_dimensions, key)
        if isinstance(value, str):
            normalized = value.strip().lower().replace(" ", "_")
            if normalized:
                return normalized
    return None


def _hint_strength(tone_dimensions: dict[str, Any], *keys: str) -> int:
    raw = _extract_hint_text(tone_dimensions, *keys)
    if raw is None:
        return 0
    if raw in {"very_high", "extreme", "explicit", "hostile", "positive_legitimizing"}:
        return 3
    if raw in {"high", "strong", "critical", "accusatory", "implied"}:
        return 3
    if raw in {"medium", "moderate", "mixed", "present", "partial"}:
        return 2
    if raw in {"low", "mild", "subtle", "neutral", "none", "absent"}:
        return 1
    return 2


# Existing helpers follow mostly unchanged.


def _coerce_collection(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        items: list[Any] = []
        for key, item in value.items():
            if isinstance(item, bool):
                if item and _usable_framing_key(key):
                    items.append(key)
                continue
            if isinstance(item, (list, tuple)):
                if _usable_framing_key(key):
                    items.append(key)
                items.extend(item)
                continue
            if isinstance(item, dict):
                if _usable_framing_key(key):
                    items.append(key)
                items.append(item)
                continue
            if isinstance(item, str):
                if _usable_framing_key(key):
                    items.append(key)
                items.append(item)
                continue
            if _usable_framing_key(key):
                items.append(key)
        return items
    return [value]


def _coerce_evidence_collection(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, dict):
        if any(key in value for key in ("text", "span", "quote", "context")):
            return [value]
        return [item for item in value.values() if item is not None]
    return [value]


def _usable_framing_key(key: str) -> bool:
    normalized = (key or "").strip().lower().replace(" ", "_")
    return bool(normalized) and normalized not in {
        "main_narrative",
        "key_framing_elements",
        "balance",
        "sources_represented",
        "device_1",
        "device_2",
        "device_3",
    }


def _coerce_bool_signal(key: str, value: bool) -> str:
    normalized_key = key.strip().lower()
    if normalized_key in {"sensationalism", "loaded_language", "emotional_tone", "alarmism"}:
        return "true" if value else "false"
    if normalized_key in {"neutral_reporting", "informational_balance"}:
        return "false" if value else "absent"
    return "true" if value else "false"


def _repair_bias_score(
    value: Any, repair_warnings: list[str], dropped_fields: list[str]
) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            coerced = float(value.strip())
        except ValueError:
            dropped_fields.append("bias_score")
            repair_warnings.append(f"repair_dropped_field: bias_score={value!r}")
            return None
        repair_warnings.append(f"repair_coerced_numeric_string: bias_score={value!r} -> {coerced}")
        return coerced
    dropped_fields.append("bias_score")
    repair_warnings.append(f"repair_dropped_field: bias_score type={type(value).__name__}")
    return None


def _repair_confidence(
    value: Any, field_name: str, repair_warnings: list[str], dropped_fields: list[str]
) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in CONFIDENCE_LABEL_ALIASES:
            mapped = CONFIDENCE_LABEL_ALIASES[normalized]
            repair_warnings.append(
                f"repair_confidence_label_mapped: {field_name}={value!r} -> {mapped}"
            )
            return mapped
        try:
            mapped = float(normalized)
        except ValueError:
            dropped_fields.append(field_name)
            repair_warnings.append(
                f"repair_dropped_field: {field_name} unsupported confidence label {value!r}"
            )
            return None
        repair_warnings.append(f"repair_coerced_numeric_string: {field_name}={value!r} -> {mapped}")
        return mapped
    if isinstance(value, dict):
        for key in ("value", "score", "confidence", "level", "label"):
            if key in value:
                nested = _repair_confidence(
                    value.get(key), f"{field_name}.{key}", repair_warnings, dropped_fields
                )
                if nested is not None:
                    repair_warnings.append(
                        f"repair_confidence_object_extracted: {field_name}.{key} -> {nested}"
                    )
                    return nested
        for nested_key, nested_value in value.items():
            nested = _repair_confidence(
                nested_value, f"{field_name}.{nested_key}", repair_warnings, dropped_fields
            )
            if nested is not None:
                repair_warnings.append(
                    f"repair_confidence_object_extracted: {field_name}.{nested_key} -> {nested}"
                )
                return nested
        dropped_fields.append(field_name)
        repair_warnings.append(
            f"repair_dropped_field: {field_name} confidence object had no usable value"
        )
        return None
    dropped_fields.append(field_name)
    repair_warnings.append(f"repair_dropped_field: {field_name} type={type(value).__name__}")
    return None


def _repair_text_like(
    value: Any,
    *,
    field_name: str,
    object_keys: tuple[str, ...],
    repair_warnings: list[str],
    dropped_fields: list[str],
    min_length: int,
) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, dict):
        extracted = _extract_text_from_object(value, keys=object_keys, min_length=min_length)
        if extracted is not None:
            repair_warnings.append(f"repair_object_text_extracted: {field_name}")
            return extracted
        dropped_fields.append(field_name)
        repair_warnings.append(f"repair_dropped_field: {field_name} object had no usable text")
        return None
    dropped_fields.append(field_name)
    repair_warnings.append(f"repair_dropped_field: {field_name} type={type(value).__name__}")
    return None


def _repair_tone_dimensions(value: Any, repair_warnings: list[str]) -> dict[str, Any]:
    if isinstance(value, list):
        flattened: dict[str, Any] = {}
        for idx, item in enumerate(value):
            if isinstance(item, dict):
                flattened[f"item_{idx}"] = item
        if flattened:
            repair_warnings.append("repair_regularized_tone_dimensions_list")
        value = flattened
    if not isinstance(value, dict):
        return {}
    repaired: dict[str, Any] = {}
    for key, raw_value in value.items():
        if isinstance(raw_value, dict):
            nested: dict[str, Any] = {}
            for nested_key in ("value", "valence", "level", "label", "description", "confidence"):
                if nested_key in raw_value:
                    nested[nested_key] = raw_value.get(nested_key)
            repaired[key] = nested or raw_value
            if nested:
                repair_warnings.append(f"repair_regularized_nested_tone: {key}")
        elif isinstance(raw_value, bool):
            repaired[key] = _coerce_bool_signal(key, raw_value)
            repair_warnings.append(f"repair_regularized_boolean_tone: {key}")
        else:
            repaired[key] = raw_value
    return repaired


def _repair_framing_devices(
    values: Any,
    repair_warnings: list[str],
    dropped_fields: list[str],
    truncated_fields: list[str],
) -> list[Any]:
    repaired = _coerce_collection(values)
    if len(repaired) > RAW_FRAMING_WORKING_CAP:
        truncated_fields.append("framing_devices")
        repair_warnings.append(
            f"repair_truncated_framing_devices: {len(repaired)} -> {RAW_FRAMING_WORKING_CAP}"
        )
        repaired = repaired[:RAW_FRAMING_WORKING_CAP]
    normalized: list[Any] = []
    for item in repaired:
        if isinstance(item, str):
            normalized.append(item)
            continue
        if isinstance(item, dict):
            if len(item) == 1:
                only_key = next(iter(item))
                only_value = item[only_key]
                if isinstance(only_value, (list, tuple)) and _usable_framing_key(only_key):
                    repair_warnings.append("repair_framing_device_map_key_promoted")
                    normalized.append(only_key)
                    continue
            extracted = _extract_text_from_object(
                item, keys=("device", "type", "description", "label", "name"), min_length=3
            )
            if extracted is not None:
                repair_warnings.append("repair_framing_device_object_extracted")
                normalized.append(extracted)
                continue
        dropped_fields.append("framing_devices")
        repair_warnings.append(f"repair_dropped_field: framing_device={item!r}")
    return normalized


def _repair_evidence_spans(
    values: Any,
    repair_warnings: list[str],
    dropped_fields: list[str],
    truncated_fields: list[str],
) -> list[Any]:
    repaired = _coerce_evidence_collection(values)
    if len(repaired) > RAW_EVIDENCE_WORKING_CAP:
        truncated_fields.append("evidence_spans")
        repair_warnings.append(
            f"repair_truncated_evidence_spans: {len(repaired)} -> {RAW_EVIDENCE_WORKING_CAP}"
        )
        repaired = repaired[:RAW_EVIDENCE_WORKING_CAP]
    normalized: list[Any] = []
    for item in repaired:
        if isinstance(item, str):
            normalized.append(item)
            continue
        if isinstance(item, dict):
            normalized_item = {
                "type": item.get("type") or item.get("location"),
                "text": item.get("text")
                or item.get("span")
                or item.get("quote")
                or item.get("context"),
                "note": item.get("note")
                or item.get("explanation")
                or item.get("justification")
                or item.get("function"),
            }
            if normalized_item["text"]:
                repair_warnings.append("repair_regularized_evidence_object")
                normalized.append(normalized_item)
                continue
        dropped_fields.append("evidence_spans")
        repair_warnings.append(f"repair_dropped_field: evidence_span={item!r}")
    return normalized


def _extract_bias_label(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    for key in ("direction", "bias", "bias_type", "bias_direction", "position", "orientation"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def _extract_nested_choice(container: dict[str, Any], key: str) -> Any:
    value = container.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        for nested_key in ("value", "valence", "level", "label", "description"):
            candidate = value.get(nested_key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
            if isinstance(candidate, bool):
                return "true" if candidate else "false"
    return None


def _extract_text_from_object(
    value: dict[str, Any], *, keys: tuple[str, ...], min_length: int
) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str):
            cleaned = candidate.strip()
            if len(cleaned) >= min_length:
                return cleaned
    return None


def _normalize_choice(
    value: Any,
    *,
    allowed: set[str],
    aliases: dict[str, str],
    default: str,
    warnings: list[str],
    label: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        warnings.append(f"unresolved {label}; using {default!r}")
        return default
    raw_value = value.strip().lower().replace(" ", "_")
    normalized = aliases.get(raw_value, raw_value)
    if normalized in allowed:
        if normalized != raw_value:
            warnings.append(f"mapped {label}={value!r} -> {normalized!r}")
        return normalized
    warnings.append(f"unmapped {label}={value!r}; using {default!r}")
    return default


def _resolve_confidence(
    explicit: float | None,
    global_confidence: float | None,
    fallback: float,
    unclear_cap: float | None,
) -> float:
    value = (
        explicit
        if explicit is not None
        else global_confidence
        if global_confidence is not None
        else fallback
    )
    value = max(0.0, min(1.0, float(value)))
    if unclear_cap is not None:
        value = min(value, unclear_cap)
    return round(value, 3)


def _resolve_bias_score(explicit: float | None, bias_label: str) -> float:
    if explicit is None:
        return BIAS_SCORE_BY_LABEL[bias_label]
    value = max(-1.0, min(1.0, float(explicit)))
    if bias_label == "unclear":
        return round(max(-0.2, min(0.2, value)), 3)
    if bias_label == "center":
        return round(max(-0.3, min(0.3, value)), 3)
    return round(value, 3)


def _normalize_framing_devices(
    raw_values: list[Any], warnings: list[str]
) -> tuple[list[str], list[str]]:
    normalized: list[str] = []
    seen: set[str] = set()
    unmapped: list[str] = []
    for item in raw_values:
        if not isinstance(item, str) or not item.strip():
            continue
        raw = item.strip().lower().replace(" ", "_")
        mapped = FRAMING_DEVICE_ALIASES.get(raw, raw)
        if mapped not in FRAMING_DEVICE_VALUES:
            warnings.append(f"dropped framing_device={item!r}")
            unmapped.append(item.strip())
            continue
        if mapped in seen:
            continue
        seen.add(mapped)
        normalized.append(mapped)
        if len(normalized) >= 5:
            break
    return normalized, unmapped[:12]


def _normalize_evidence_spans(raw_values: list[Any], warnings: list[str]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in raw_values:
        if isinstance(item, str):
            text = item.strip()
            if len(text) < 3:
                continue
            normalized.append(
                {
                    "type": "body",
                    "text": text[:400],
                    "note": "quoted evidence span from article body",
                }
            )
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("span") or "").strip()
            note = str(
                item.get("note")
                or item.get("explanation")
                or item.get("justification")
                or "quoted evidence span"
            ).strip()
            span_type = str(item.get("type") or item.get("location") or "body").strip().lower()
            span_type = {
                "titular": "headline",
                "hechos": "body",
                "atribución_fuente": "body",
                "atribucion_fuente": "body",
                "respuesta_emergencias": "body",
            }.get(span_type, span_type)
            if span_type not in EVIDENCE_SPAN_TYPES:
                warnings.append(f"mapped evidence type {span_type!r} -> 'body'")
                span_type = "body"
            if len(text) < 3:
                continue
            if len(note) < 3:
                note = "quoted evidence span"
            normalized.append({"type": span_type, "text": text[:400], "note": note[:240]})
        if len(normalized) >= 3:
            break
    if not normalized:
        raise EditorialNormalizationError("normalization failed: no usable evidence_spans")
    return normalized


def _normalize_rationale(repaired: RepairedEditorialPayload, warnings: list[str]) -> str:
    candidates = [repaired.rationale, repaired.notes, repaired.uncertainty_reason]
    for candidate in candidates:
        if isinstance(candidate, str):
            cleaned = candidate.strip()
            if len(cleaned) >= 12:
                return cleaned[:1200]
    warnings.append("rationale missing or too short; using conservative fallback rationale")
    return (
        "Normalized conservatively from raw model output because the original "
        "rationale was missing or too short."
    )
