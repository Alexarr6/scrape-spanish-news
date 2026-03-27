from __future__ import annotations

from typing import Any

from src.analysis.editorial.normalization.constants import (
    CONFIDENCE_LABEL_ALIASES,
    RAW_EVIDENCE_WORKING_CAP,
    RAW_FRAMING_WORKING_CAP,
)


def coerce_collection(value: Any) -> list[Any]:
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
                if item and usable_framing_key(key):
                    items.append(key)
                continue
            if isinstance(item, (list, tuple)):
                if usable_framing_key(key):
                    items.append(key)
                items.extend(item)
                continue
            if isinstance(item, dict):
                if usable_framing_key(key):
                    items.append(key)
                items.append(item)
                continue
            if isinstance(item, str):
                if usable_framing_key(key):
                    items.append(key)
                items.append(item)
                continue
            if usable_framing_key(key):
                items.append(key)
        return items
    return [value]


def coerce_evidence_collection(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, dict):
        if any(key in value for key in ("text", "span", "quote", "context")):
            return [value]
        return [item for item in value.values() if item is not None]
    return [value]


def usable_framing_key(key: str) -> bool:
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


def coerce_bool_signal(key: str, value: bool) -> str:
    normalized_key = key.strip().lower()
    if normalized_key in {"sensationalism", "loaded_language", "emotional_tone", "alarmism"}:
        return "true" if value else "false"
    if normalized_key in {"neutral_reporting", "informational_balance"}:
        return "false" if value else "absent"
    return "true" if value else "false"


def repair_bias_score(
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


def repair_confidence(
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
                nested = repair_confidence(
                    value.get(key), f"{field_name}.{key}", repair_warnings, dropped_fields
                )
                if nested is not None:
                    repair_warnings.append(
                        f"repair_confidence_object_extracted: {field_name}.{key} -> {nested}"
                    )
                    return nested
        for nested_key, nested_value in value.items():
            nested = repair_confidence(
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


def repair_text_like(
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
        extracted = extract_text_from_object(value, keys=object_keys, min_length=min_length)
        if extracted is not None:
            repair_warnings.append(f"repair_object_text_extracted: {field_name}")
            return extracted
        dropped_fields.append(field_name)
        repair_warnings.append(f"repair_dropped_field: {field_name} object had no usable text")
        return None
    dropped_fields.append(field_name)
    repair_warnings.append(f"repair_dropped_field: {field_name} type={type(value).__name__}")
    return None


def repair_tone_dimensions(value: Any, repair_warnings: list[str]) -> dict[str, Any]:
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
            repaired[key] = coerce_bool_signal(key, raw_value)
            repair_warnings.append(f"repair_regularized_boolean_tone: {key}")
        else:
            repaired[key] = raw_value
    return repaired


def repair_framing_devices(
    values: Any,
    repair_warnings: list[str],
    dropped_fields: list[str],
    truncated_fields: list[str],
) -> list[Any]:
    repaired = coerce_collection(values)
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
                if isinstance(only_value, (list, tuple)) and usable_framing_key(only_key):
                    repair_warnings.append("repair_framing_device_map_key_promoted")
                    normalized.append(only_key)
                    continue
            extracted = extract_text_from_object(
                item, keys=("device", "type", "description", "label", "name"), min_length=3
            )
            if extracted is not None:
                repair_warnings.append("repair_framing_device_object_extracted")
                normalized.append(extracted)
                continue
        dropped_fields.append("framing_devices")
        repair_warnings.append(f"repair_dropped_field: framing_device={item!r}")
    return normalized


def repair_evidence_spans(
    values: Any,
    repair_warnings: list[str],
    dropped_fields: list[str],
    truncated_fields: list[str],
) -> list[Any]:
    repaired = coerce_evidence_collection(values)
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


def extract_bias_label(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    for key in ("direction", "bias", "bias_type", "bias_direction", "position", "orientation"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def extract_text_from_object(
    value: dict[str, Any], *, keys: tuple[str, ...], min_length: int
) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str):
            cleaned = candidate.strip()
            if len(cleaned) >= min_length:
                return cleaned
    return None
