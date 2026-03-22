from __future__ import annotations

import pytest

from src.analysis.editorial_normalization import (
    EditorialNormalizationError,
    normalize_editorial_payload,
)

MINIMAX_STYLE_RAW = {
    "article_type": "breaking_news_crime_report",
    "ideological_bias_framing": "unclear",
    "tone_dimensions": {
        "formality": "informal_to_neutral",
        "emotionality": "neutral",
        "sensationalism": "none",
        "polarization": "none",
    },
    "framing_devices": [
        "official_source_attribution",
        "factual_objective_reporting",
        "chronological_sequencing",
        "no_speculation_or_context",
    ],
    "rationale": (
        "This is a straightforward factual crime report describing a knife attack incident. "
        "The article contains no ideological framing, political content, editorial commentary, "
        "or interpretive language."
    ),
    "evidence_spans": [
        "Tres hombres de entre 19 y 46 años han resultado heridos con arma blanca",
        "Según han informado a ABC fuentes del Servicio de Emergencias 112",
    ],
    "confidence": 0.85,
}


def test_normalize_editorial_payload_salvages_minimax_style_raw_shape() -> None:
    result = normalize_editorial_payload(MINIMAX_STYLE_RAW)

    assert result.final_payload.article_type == "news_report"
    assert result.final_payload.article_type_confidence == 0.55
    assert result.final_payload.bias_label == "unclear"
    assert result.final_payload.bias_score == 0.0
    assert result.final_payload.bias_confidence == 0.6
    assert result.final_payload.tone_emotional == "calm"
    assert result.final_payload.tone_target == "unclear"
    assert result.final_payload.opinionatedness == "unclear"
    assert result.final_payload.sensationalism == "low"
    assert result.final_payload.rhetorical_certainty == "unclear"
    assert result.final_payload.framing_devices == []
    assert result.final_payload.evidence_spans[0].type == "body"
    assert any("mapped article_type" in warning for warning in result.warnings)
    assert any("dropped framing_device" in warning for warning in result.warnings)


def test_normalize_editorial_payload_uses_aliases_and_global_confidence_conservatively() -> None:
    result = normalize_editorial_payload(
        {
            "article_type": "op_ed",
            "bias_label": "center-right",
            "tone_dimensions": {
                "target": "negative",
                "opinionatedness": "commentary",
                "sensationalism": "moderate",
                "certainty": "direct",
            },
            "confidence": 0.72,
            "framing_devices": ["public_safety", "competence", "public_safety"],
            "evidence_spans": [
                {
                    "location": "headline",
                    "text": "El Gobierno vuelve a fallar en seguridad",
                    "explanation": "Blames the government in direct terms",
                }
            ],
            "rationale": "The piece uses a clear evaluative frame and presents blame directly.",
        }
    )

    assert result.final_payload.article_type == "opinion"
    assert result.final_payload.bias_label == "center_right"
    assert result.final_payload.bias_confidence == 0.6
    assert result.final_payload.tone_target == "critical"
    assert result.final_payload.opinionatedness == "opinionated"
    assert result.final_payload.sensationalism == "medium"
    assert result.final_payload.rhetorical_certainty == "assertive"
    assert result.final_payload.framing_devices == [
        "public_order_security",
        "governance_competence",
    ]
    assert result.final_payload.evidence_spans[0].type == "headline"


def test_normalize_editorial_payload_salvages_spanish_bias_object_shape_conservatively() -> None:
    result = normalize_editorial_payload(
        {
            "article_type": "noticia_accidente",
            "ideological_bias_framing": {
                "bias_type": "sin_sesgo_claro",
                "direction": "unclear",
                "confidence": 0.7,
                "justification": (
                    "El texto describe un accidente y la respuesta de emergencias con tono "
                    "informativo; no hay argumentación política ni encuadres ideológicos."
                ),
            },
            "tone_dimensions": {
                "overall_tone": "informativo_y_sobrio",
                "sensationalism": "bajo",
                "emotionality": "baja",
                "urgency": "baja",
                "confidence": 0.75,
            },
            "framing_devices": [
                "encuadre_de_sucesos_basado_en_hechos",
                "atribución_a_fuentes_institucionales/medios_de_emergencia",
            ],
            "rationale": (
                "La estructura es típica de una noticia de sucesos y no incluye juicios "
                "valorativos ni atribuciones políticas."
            ),
            "evidence_spans": [
                {
                    "span": "Fallece un motorista de 51 años al salirse de la vía",
                    "type": "titular",
                },
                {
                    "span": "Un hombre de 51 años ha fallecido este domingo al salirse de la vía.",
                    "type": "hechos",
                },
            ],
            "confidence": 0.78,
        }
    )

    assert result.final_payload.article_type == "news_report"
    assert result.final_payload.bias_label == "unclear"
    assert result.final_payload.bias_score == 0.0
    assert result.final_payload.bias_confidence == 0.6
    assert result.final_payload.tone_emotional == "calm"
    assert result.final_payload.sensationalism == "low"
    assert result.final_payload.evidence_spans[0].type == "headline"
    assert result.final_payload.evidence_spans[0].text.startswith("Fallece un motorista")
    assert result.final_payload.framing_devices == []
    assert any("mapped article_type" in warning for warning in result.warnings)
    assert any("dropped framing_device" in warning for warning in result.warnings)


def test_normalize_editorial_payload_raises_when_no_usable_evidence_exists() -> None:
    with pytest.raises(EditorialNormalizationError, match="no usable evidence_spans"):
        normalize_editorial_payload(
            {
                "article_type": "news",
                "framing_devices": [],
                "evidence_spans": [],
                "rationale": "Too little support to persist this safely.",
            }
        )
