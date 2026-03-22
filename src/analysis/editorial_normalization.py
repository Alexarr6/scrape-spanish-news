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
    "sin_sesgo_claro": "unclear",
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
RAW_FRAMING_WORKING_CAP = 8


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


def normalize_editorial_payload(raw_payload: dict[str, Any]) -> EditorialNormalizationResult:
    try:
        raw = ArticleEditorialAnalysisRawPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise EditorialNormalizationError(f"raw payload validation failed: {exc}") from exc

    repaired = repair_editorial_raw_payload(raw)
    normalization_warnings: list[str] = []
    unclear_reasons: set[str] = set()

    article_type = _normalize_choice(
        repaired.article_type,
        allowed=set(ARTICLE_TYPES) | {"unclear"},
        aliases=ARTICLE_TYPE_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="article_type",
    )
    if article_type == "unclear":
        unclear_reasons.add("mapping_unresolved")
    article_type_confidence = _resolve_confidence(
        explicit=repaired.article_type_confidence,
        global_confidence=repaired.confidence,
        fallback=0.3 if article_type == "unclear" else 0.55,
        unclear_cap=0.6 if article_type == "unclear" else None,
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
    if bias_label == "unclear":
        if raw_bias_label is None or str(raw_bias_label).strip().lower() in {"unclear", "neutral", "none"}:
            unclear_reasons.add("semantic_weak_signal")
        else:
            unclear_reasons.add("mapping_unresolved")
    bias_score = _resolve_bias_score(repaired.bias_score, bias_label)
    bias_confidence = _resolve_confidence(
        explicit=repaired.bias_confidence,
        global_confidence=repaired.confidence,
        fallback=0.3 if bias_label == "unclear" else 0.5,
        unclear_cap=0.6 if bias_label == "unclear" else None,
    )

    tone_dimensions = repaired.tone_dimensions or {}
    tone_emotional_source = (
        repaired.tone_emotional
        or _extract_nested_choice(tone_dimensions, "emotionality")
        or _extract_nested_choice(tone_dimensions, "emotional_valence")
        or tone_dimensions.get("overall_tone")
    )
    tone_emotional = _normalize_choice(
        tone_emotional_source,
        allowed=set(TONE_EMOTIONAL_VALUES),
        aliases=TONE_EMOTIONAL_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="tone_emotional",
    )
    tone_target = _normalize_choice(
        repaired.tone_target or tone_dimensions.get("target") or tone_dimensions.get("polarity"),
        allowed=set(TONE_TARGET_VALUES),
        aliases=TONE_TARGET_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="tone_target",
    )
    opinionatedness = _normalize_choice(
        repaired.opinionatedness
        or tone_dimensions.get("opinionatedness")
        or tone_dimensions.get("style"),
        allowed=set(OPINIONATEDNESS_VALUES),
        aliases=OPINIONATEDNESS_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="opinionatedness",
    )
    sensationalism = _normalize_choice(
        repaired.sensationalism
        or _extract_nested_choice(tone_dimensions, "sensationalism")
        or _extract_nested_choice(tone_dimensions, "alarmism"),
        allowed=set(SENSATIONALISM_VALUES),
        aliases=SENSATIONALISM_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="sensationalism",
    )
    rhetorical_certainty = _normalize_choice(
        repaired.rhetorical_certainty
        or tone_dimensions.get("rhetorical_certainty")
        or tone_dimensions.get("certainty"),
        allowed=set(RHETORICAL_CERTAINTY_VALUES),
        aliases=RHETORICAL_CERTAINTY_ALIASES,
        default="unclear",
        warnings=normalization_warnings,
        label="rhetorical_certainty",
    )

    framing_devices = _normalize_framing_devices(repaired.framing_devices, normalization_warnings)
    evidence_spans = _normalize_evidence_spans(repaired.evidence_spans, normalization_warnings)
    rationale = _normalize_rationale(repaired, normalization_warnings)

    if repaired.dropped_fields or repaired.truncated_fields:
        unclear_reasons.add("repair_data_loss")
    if bias_label == "unclear" and repaired.dropped_fields:
        unclear_reasons.add("mapping_unresolved")
    if bias_label == "unclear" and raw_bias_label is None and not repaired.dropped_fields:
        unclear_reasons.add("semantic_weak_signal")

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

    return EditorialNormalizationResult(
        raw_payload=raw,
        repaired_payload=repaired,
        final_payload=final_payload,
        warnings=tuple([*repaired.repair_warnings, *normalization_warnings]),
        repair_warnings=repaired.repair_warnings,
        normalization_warnings=tuple(normalization_warnings),
        dropped_fields=repaired.dropped_fields,
        truncated_fields=repaired.truncated_fields,
        unclear_reasons=tuple(sorted(unclear_reasons)),
    )


def repair_editorial_raw_payload(
    raw: ArticleEditorialAnalysisRawPayload,
) -> RepairedEditorialPayload:
    repair_warnings: list[str] = []
    dropped_fields: list[str] = []
    truncated_fields: list[str] = []

    confidence = _repair_confidence(raw.confidence, "confidence", repair_warnings, dropped_fields)
    article_type_confidence = _repair_confidence(
        raw.article_type_confidence,
        "article_type_confidence",
        repair_warnings,
        dropped_fields,
    )
    bias_confidence = _repair_confidence(
        raw.bias_confidence,
        "bias_confidence",
        repair_warnings,
        dropped_fields,
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
        object_keys=("summary", "description", "note"),
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
    value: Any,
    field_name: str,
    repair_warnings: list[str],
    dropped_fields: list[str],
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
        else:
            repaired[key] = raw_value
    return repaired


def _repair_framing_devices(
    values: list[Any],
    repair_warnings: list[str],
    dropped_fields: list[str],
    truncated_fields: list[str],
) -> list[Any]:
    repaired = list(values)
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
            extracted = _extract_text_from_object(
                item,
                keys=("device", "type", "description", "label", "name"),
                min_length=3,
            )
            if extracted is not None:
                repair_warnings.append("repair_framing_device_object_extracted")
                normalized.append(extracted)
                continue
        dropped_fields.append("framing_devices")
        repair_warnings.append(f"repair_dropped_field: framing_device={item!r}")
    return normalized


def _repair_evidence_spans(
    values: list[Any],
    repair_warnings: list[str],
    dropped_fields: list[str],
    truncated_fields: list[str],
) -> list[Any]:
    repaired = list(values)
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
    for key in ("direction", "bias", "bias_type", "bias_direction"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def _extract_nested_choice(container: dict[str, Any], key: str) -> Any:
    value = container.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for nested_key in ("value", "valence", "level", "label", "description"):
            candidate = value.get(nested_key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
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
    if explicit is not None:
        value = explicit
    elif global_confidence is not None:
        value = global_confidence
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
    for item in raw_values:
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
