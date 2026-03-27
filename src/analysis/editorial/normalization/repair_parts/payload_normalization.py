from __future__ import annotations

from typing import Any

from src.analysis.editorial.normalization.constants import (
    BIAS_SCORE_BY_LABEL,
    EVIDENCE_SPAN_TYPES,
    FRAMING_DEVICE_ALIASES,
    FRAMING_DEVICE_VALUES,
)
from src.analysis.editorial.normalization.types import (
    EditorialNormalizationError,
    RepairedEditorialPayload,
)


def normalize_choice(
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


def resolve_confidence(
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


def resolve_bias_score(explicit: float | None, bias_label: str) -> float:
    if explicit is None:
        return BIAS_SCORE_BY_LABEL[bias_label]
    value = max(-1.0, min(1.0, float(explicit)))
    if bias_label == "unclear":
        return round(max(-0.2, min(0.2, value)), 3)
    if bias_label == "center":
        return round(max(-0.3, min(0.3, value)), 3)
    return round(value, 3)


def normalize_framing_devices(
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


def normalize_evidence_spans(raw_values: list[Any], warnings: list[str]) -> list[dict[str, str]]:
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


def normalize_rationale(repaired: RepairedEditorialPayload, warnings: list[str]) -> str:
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
