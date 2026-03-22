from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.analysis.contracts import (
    ArticleEditorialAnalysisPayload,
    ArticleEditorialAnalysisRawPayload,
)
from src.analysis.llm_client import build_editorial_analysis_prompt, editorial_analysis_json_schema

VALID_PAYLOAD = {
    "article_type": "analysis",
    "article_type_confidence": 0.72,
    "bias_label": "center_left",
    "bias_score": -0.34,
    "bias_confidence": 0.68,
    "tone_emotional": "loaded",
    "tone_target": "critical",
    "opinionatedness": "interpretive",
    "sensationalism": "medium",
    "rhetorical_certainty": "assertive",
    "framing_devices": ["humanitarian", "moral_judgment"],
    "evidence_spans": [
        {
            "type": "headline",
            "text": "El recorte agrava la vulnerabilidad",
            "note": "Frames policy as social harm",
        }
    ],
    "rationale": (
        "The article foregrounds harm, uses morally loaded framing, and criticizes "
        "the policy choice with clear evaluative language."
    ),
}


def test_editorial_payload_accepts_valid_bounded_input() -> None:
    payload = ArticleEditorialAnalysisPayload.model_validate(VALID_PAYLOAD)

    assert payload.bias_label == "center_left"
    assert payload.framing_devices == ["humanitarian", "moral_judgment"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("framing_devices", ["conflict", "conflict"]),
        ("evidence_spans", []),
        ("bias_score", 2.0),
    ],
)
def test_editorial_payload_rejects_basic_schema_violations(field: str, value: object) -> None:
    payload = dict(VALID_PAYLOAD)
    payload[field] = value

    with pytest.raises(ValidationError):
        ArticleEditorialAnalysisPayload.model_validate(payload)


def test_editorial_payload_rejects_unclear_label_with_confident_extreme_score() -> None:
    payload = dict(VALID_PAYLOAD)
    payload.update({"bias_label": "unclear", "bias_score": 0.45, "bias_confidence": 0.8})

    with pytest.raises(ValidationError):
        ArticleEditorialAnalysisPayload.model_validate(payload)


def test_raw_editorial_payload_accepts_permissive_shape_variation() -> None:
    payload = ArticleEditorialAnalysisRawPayload.model_validate(
        {
            "article_type": "noticia_accidente",
            "article_type_confidence": {"label": "moderate"},
            "ideological_bias_framing": {
                "bias_type": "sin_sesgo_claro",
                "direction": "unclear",
                "confidence": "low",
                "justification": "No hay encuadre ideológico claro.",
            },
            "confidence": "moderate",
            "framing_devices": [{"device": "public_safety"}] * 10,
            "evidence_spans": [{"span": f"Texto {idx}", "type": "hechos"} for idx in range(9)],
            "rationale": {
                "summary": "Texto factual sin encuadre ideológico claro ni carga valorativa.",
                "confidence": 0.62,
            },
            "tone_dimensions": {
                "emotional_valence": {"valence": "neutral", "confidence": 0.44},
            },
        }
    )

    assert isinstance(payload.ideological_bias_framing, dict)
    assert payload.ideological_bias_framing["bias_type"] == "sin_sesgo_claro"
    assert payload.confidence == "moderate"
    assert len(payload.evidence_spans) == 9
    assert isinstance(payload.rationale, dict)
    assert payload.rationale["summary"].startswith("Texto factual")


def test_editorial_prompt_and_schema_expose_raw_generation_contract() -> None:
    prompt = build_editorial_analysis_prompt(
        source="elpais",
        section="politica",
        published_at="2026-03-20T08:00:00+00:00",
        url="https://elpais.com/x",
        title="Título",
        summary="Resumen",
        body="Cuerpo del artículo",
    )
    schema = editorial_analysis_json_schema()

    assert "ARTICLE_METADATA:" in prompt
    assert "TITLE: Título" in prompt
    assert "portable raw JSON object" in prompt
    assert schema["additionalProperties"] is True
    assert "ideological_bias_framing" in schema["properties"]
    assert "tone_dimensions" in schema["properties"]
    assert schema["properties"]["framing_devices"]["maxItems"] == 20
    assert schema["properties"]["evidence_spans"]["maxItems"] == 20
    assert "anyOf" in schema["properties"]["confidence"]
