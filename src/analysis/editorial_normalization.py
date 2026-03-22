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
}

OPINIONATEDNESS_ALIASES = {
    "objective_reporting": "straight_reporting",
    "factual_reporting": "straight_reporting",
    "news_reporting": "straight_reporting",
    "analysis": "interpretive",
    "commentary": "opinionated",
    "advocacy": "activist",
    "neutral": "straight_reporting",
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
}

RHETORICAL_CERTAINTY_ALIASES = {
    "measured": "cautious",
    "qualified": "cautious",
    "neutral": "assertive",
    "factual": "assertive",
    "direct": "assertive",
    "categorical": "absolute",
    "dogmatic": "absolute",
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
}


@dataclass(frozen=True)
class EditorialNormalizationResult:
    raw_payload: ArticleEditorialAnalysisRawPayload
    final_payload: ArticleEditorialAnalysisPayload
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class EditorialNormalizationError(Exception):
    message: str
    raw_payload: ArticleEditorialAnalysisRawPayload | None = None
    warnings: tuple[str, ...] = ()

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


def normalize_editorial_payload(raw_payload: dict[str, Any]) -> EditorialNormalizationResult:
    try:
        raw = ArticleEditorialAnalysisRawPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise EditorialNormalizationError(f"raw payload validation failed: {exc}") from exc

    warnings: list[str] = []
    article_type = _normalize_choice(
        raw.article_type,
        allowed=set(ARTICLE_TYPES) | {"unclear"},
        aliases=ARTICLE_TYPE_ALIASES,
        default="unclear",
        warnings=warnings,
        label="article_type",
    )
    article_type_confidence = _resolve_confidence(
        explicit=raw.article_type_confidence,
        global_confidence=raw.confidence,
        fallback=0.3 if article_type == "unclear" else 0.55,
        unclear_cap=0.6 if article_type == "unclear" else None,
        max_from_global=0.55,
    )

    raw_bias_label = raw.bias_label or raw.ideological_bias_framing
    bias_label = _normalize_choice(
        raw_bias_label,
        allowed=set(BIAS_LABELS),
        aliases=BIAS_LABEL_ALIASES,
        default="unclear",
        warnings=warnings,
        label="bias_label",
    )
    bias_score = _resolve_bias_score(raw.bias_score, bias_label)
    bias_confidence = _resolve_confidence(
        explicit=raw.bias_confidence,
        global_confidence=raw.confidence,
        fallback=0.3 if bias_label == "unclear" else 0.5,
        unclear_cap=0.6 if bias_label == "unclear" else None,
        max_from_global=0.6,
    )

    tone_dimensions = raw.tone_dimensions or {}
    tone_emotional = _normalize_choice(
        raw.tone_emotional or tone_dimensions.get("emotionality"),
        allowed=set(TONE_EMOTIONAL_VALUES),
        aliases=TONE_EMOTIONAL_ALIASES,
        default="unclear",
        warnings=warnings,
        label="tone_emotional",
    )
    tone_target = _normalize_choice(
        raw.tone_target or tone_dimensions.get("target") or tone_dimensions.get("polarity"),
        allowed=set(TONE_TARGET_VALUES),
        aliases=TONE_TARGET_ALIASES,
        default="unclear",
        warnings=warnings,
        label="tone_target",
    )
    opinionatedness_source = (
        raw.opinionatedness
        or tone_dimensions.get("opinionatedness")
        or tone_dimensions.get("style")
    )
    opinionatedness = _normalize_choice(
        opinionatedness_source,
        allowed=set(OPINIONATEDNESS_VALUES),
        aliases=OPINIONATEDNESS_ALIASES,
        default="unclear",
        warnings=warnings,
        label="opinionatedness",
    )
    sensationalism = _normalize_choice(
        raw.sensationalism or tone_dimensions.get("sensationalism"),
        allowed=set(SENSATIONALISM_VALUES),
        aliases=SENSATIONALISM_ALIASES,
        default="unclear",
        warnings=warnings,
        label="sensationalism",
    )
    rhetorical_certainty_source = (
        raw.rhetorical_certainty
        or tone_dimensions.get("rhetorical_certainty")
        or tone_dimensions.get("certainty")
    )
    rhetorical_certainty = _normalize_choice(
        rhetorical_certainty_source,
        allowed=set(RHETORICAL_CERTAINTY_VALUES),
        aliases=RHETORICAL_CERTAINTY_ALIASES,
        default="unclear",
        warnings=warnings,
        label="rhetorical_certainty",
    )

    framing_devices = _normalize_framing_devices(raw.framing_devices, warnings)
    evidence_spans = _normalize_evidence_spans(raw.evidence_spans, warnings)
    rationale = _normalize_rationale(raw, warnings)

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
            warnings=tuple(warnings),
        ) from exc

    return EditorialNormalizationResult(
        raw_payload=raw,
        final_payload=final_payload,
        warnings=tuple(warnings),
    )


def _extract_bias_label(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    direction = value.get("direction")
    if isinstance(direction, str) and direction.strip() and direction.strip().lower() != "unclear":
        return direction
    bias_type = value.get("bias_type")
    if isinstance(bias_type, str) and bias_type.strip():
        return bias_type
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
        return default
    normalized = value.strip().lower().replace(" ", "_")
    normalized = aliases.get(normalized, normalized)
    if normalized in allowed:
        if normalized != value.strip().lower().replace(" ", "_"):
            warnings.append(f"mapped {label}={value!r} -> {normalized!r}")
        return normalized
    warnings.append(f"unmapped {label}={value!r}; using {default!r}")
    return default


def _resolve_confidence(
    explicit: float | None,
    global_confidence: float | None,
    fallback: float,
    unclear_cap: float | None,
    max_from_global: float | None = None,
) -> float:
    if explicit is not None:
        value = explicit
    elif global_confidence is not None:
        value = global_confidence
        if max_from_global is not None:
            value = min(value, max_from_global)
    else:
        value = fallback
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


def _normalize_framing_devices(raw_values: list[Any], warnings: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_values[:8]:
        if not isinstance(item, str) or not item.strip():
            continue
        raw = item.strip().lower().replace(" ", "_")
        mapped = FRAMING_DEVICE_ALIASES.get(raw, raw)
        if mapped not in FRAMING_DEVICE_VALUES:
            warnings.append(f"dropped framing_device={item!r}")
            continue
        if mapped in seen:
            continue
        seen.add(mapped)
        normalized.append(mapped)
        if len(normalized) >= 5:
            break
    return normalized


def _normalize_evidence_spans(raw_values: list[Any], warnings: list[str]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in raw_values[:6]:
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


def _normalize_rationale(raw: ArticleEditorialAnalysisRawPayload, warnings: list[str]) -> str:
    candidates = [raw.rationale, raw.notes, raw.uncertainty_reason]
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
