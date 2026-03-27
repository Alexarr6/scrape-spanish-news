from __future__ import annotations

from typing import Any

from src.analysis.editorial.normalization.types import RepairedEditorialPayload


def extract_bias_hints(repaired: RepairedEditorialPayload) -> list[str]:
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


def collect_tone_hints(
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


def resolve_tone_emotional_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.tone_emotional
        or extract_nested_choice(tone_dimensions, "emotionality")
        or extract_nested_choice(tone_dimensions, "emotional_valence")
        or extract_nested_choice(tone_dimensions, "overall_tone")
        or extract_nested_choice(tone_dimensions, "overall")
        or extract_nested_choice(tone_dimensions, "emotional_tone")
        or extract_nested_choice(tone_dimensions, "emotional_charge")
        or extract_nested_choice(tone_dimensions, "dramatic")
        or extract_nested_choice(tone_dimensions, "sentiment")
        or infer_tone_emotional_from_hints(tone_dimensions)
    )


def resolve_tone_target_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.tone_target
        or extract_nested_choice(tone_dimensions, "target")
        or extract_nested_choice(tone_dimensions, "polarity")
        or extract_nested_choice(tone_dimensions, "government_assessment")
        or extract_nested_choice(tone_dimensions, "sentiment")
        or infer_tone_target_from_hints(tone_dimensions)
    )


def resolve_opinionatedness_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.opinionatedness
        or extract_nested_choice(tone_dimensions, "opinionatedness")
        or extract_nested_choice(tone_dimensions, "style")
        or extract_nested_choice(tone_dimensions, "neutral_reporting")
        or extract_nested_choice(tone_dimensions, "partisan")
        or extract_nested_choice(tone_dimensions, "subjectivity")
        or extract_nested_choice(tone_dimensions, "analytical")
        or extract_nested_choice(tone_dimensions, "informational_balance")
        or infer_opinionatedness_from_hints(tone_dimensions)
    )


def resolve_sensationalism_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.sensationalism
        or extract_nested_choice(tone_dimensions, "sensationalism")
        or extract_nested_choice(tone_dimensions, "alarmism")
        or extract_nested_choice(tone_dimensions, "loaded_language")
        or infer_sensationalism_from_hints(tone_dimensions)
    )


def resolve_rhetorical_certainty_source(
    repaired: RepairedEditorialPayload, tone_dimensions: dict[str, Any]
) -> Any:
    return (
        repaired.rhetorical_certainty
        or extract_nested_choice(tone_dimensions, "rhetorical_certainty")
        or extract_nested_choice(tone_dimensions, "certainty")
        or extract_nested_choice(tone_dimensions, "confidence")
        or infer_rhetorical_certainty_from_hints(tone_dimensions)
    )


def infer_tone_emotional_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    accusatory = hint_strength(tone_dimensions, "accusatory")
    critical = hint_strength(tone_dimensions, "critical")
    partisanship = hint_strength(tone_dimensions, "partisancy", "partisan")
    procedural = hint_strength(tone_dimensions, "procedural")
    conflict = hint_strength(tone_dimensions, "conflict_framing")

    if max(accusatory, critical, partisanship, conflict) >= 3:
        return "inflammatory"
    if max(accusatory, critical, partisanship, conflict) >= 2:
        return "loaded"
    if procedural >= 2:
        return "calm"
    return None


def infer_tone_target_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    accusatory = hint_strength(tone_dimensions, "accusatory")
    critical = hint_strength(tone_dimensions, "critical")
    accountability = extract_hint_text(tone_dimensions, "accountability_attribution")
    mobilization = extract_hint_text(tone_dimensions, "mobilization_framing")
    procedural = hint_strength(tone_dimensions, "procedural")

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


def infer_opinionatedness_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    partisanship = hint_strength(tone_dimensions, "partisancy", "partisan")
    accusatory = hint_strength(tone_dimensions, "accusatory")
    critical = hint_strength(tone_dimensions, "critical")
    mobilization = extract_hint_text(tone_dimensions, "mobilization_framing")
    procedural = hint_strength(tone_dimensions, "procedural")

    if mobilization and any(token in mobilization for token in ("legitimizing", "advocacy")):
        return "activist"
    if partisanship >= 2 or max(accusatory, critical) >= 3:
        return "opinionated"
    if max(accusatory, critical) >= 2:
        return "interpretive"
    if procedural >= 2:
        return "straight_reporting"
    return None


def infer_sensationalism_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    accusatory = hint_strength(tone_dimensions, "accusatory")
    critical = hint_strength(tone_dimensions, "critical")
    conflict = hint_strength(tone_dimensions, "conflict_framing")
    procedural = hint_strength(tone_dimensions, "procedural")

    if max(accusatory, critical, conflict) >= 3:
        return "high"
    if max(accusatory, critical, conflict) >= 2:
        return "medium"
    if procedural >= 2:
        return "low"
    return None


def infer_rhetorical_certainty_from_hints(tone_dimensions: dict[str, Any]) -> str | None:
    accusatory = hint_strength(tone_dimensions, "accusatory")
    critical = hint_strength(tone_dimensions, "critical")
    procedural = hint_strength(tone_dimensions, "procedural")

    if max(accusatory, critical) >= 3:
        return "absolute"
    if max(accusatory, critical) >= 2:
        return "assertive"
    if procedural >= 2:
        return "cautious"
    return None


def extract_hint_text(tone_dimensions: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = extract_nested_choice(tone_dimensions, key)
        if isinstance(value, str):
            normalized = value.strip().lower().replace(" ", "_")
            if normalized:
                return normalized
    return None


def hint_strength(tone_dimensions: dict[str, Any], *keys: str) -> int:
    raw = extract_hint_text(tone_dimensions, *keys)
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


def extract_nested_choice(container: dict[str, Any], key: str) -> Any:
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
