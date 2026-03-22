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
    assert result.final_payload.bias_label == "unclear"
    assert result.final_payload.tone_emotional == "calm"
    assert result.final_payload.sensationalism == "low"
    assert result.final_payload.framing_devices == []
    assert result.final_payload.evidence_spans[0].type == "body"
    assert "semantic_weak_signal" in result.unclear_reasons
    assert any("mapped article_type" in warning for warning in result.warnings)
    assert any("dropped framing_device" in warning for warning in result.warnings)


def test_normalize_editorial_payload_coerces_confidence_labels_and_tracks_mapping_loss() -> None:
    result = normalize_editorial_payload(
        {
            "article_type": "op_ed",
            "bias_label": "center-right",
            "confidence": "moderate",
            "bias_confidence": {"label": "high"},
            "tone_dimensions": {
                "target": "negative",
                "opinionatedness": "commentary",
                "sensationalism": "moderate",
                "certainty": "direct",
            },
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

    assert result.repaired_payload.confidence == 0.5
    assert result.repaired_payload.bias_confidence == 0.75
    assert result.final_payload.article_type == "opinion"
    assert result.final_payload.bias_label == "center_right"
    assert result.final_payload.tone_target == "critical"
    assert result.final_payload.opinionatedness == "opinionated"
    assert any("repair_confidence_label_mapped" in warning for warning in result.repair_warnings)


def test_normalize_editorial_payload_repairs_object_shapes_and_nested_tone() -> None:
    result = normalize_editorial_payload(
        {
            "article_type": "news_report",
            "ideological_bias_framing": {
                "bias": "unclear",
                "confidence": 0.58,
                "framing_summary": (
                    "No hay encuadre ideológico claro; predomina una descripción factual."
                ),
            },
            "tone_dimensions": {
                "emotional_valence": {"valence": "neutral", "confidence": 0.44},
                "sensationalism": {"level": "low", "confidence": 0.31},
                "alarmism": {"level": "low", "confidence": 0.29},
            },
            "framing_devices": [
                {
                    "device": "public_safety",
                    "description": "Destaca la respuesta de emergencias y seguridad pública.",
                    "confidence": 0.51,
                },
                {
                    "type": "competence",
                    "description": "Evalúa la actuación institucional.",
                    "confidence": 0.49,
                },
            ],
            "rationale": {
                "summary": (
                    "La pieza resume hechos y atribuye información a fuentes institucionales."
                ),
                "confidence": 0.57,
            },
            "evidence_spans": [
                {
                    "quote": "Los servicios de emergencia acudieron al lugar tras el aviso.",
                    "function": "Atribuye la actuación institucional.",
                    "location": "hechos",
                }
            ],
            "confidence": 0.57,
        }
    )

    assert result.final_payload.tone_emotional == "calm"
    assert result.final_payload.sensationalism == "low"
    assert result.final_payload.framing_devices == [
        "public_order_security",
        "governance_competence",
    ]
    assert result.final_payload.rationale.startswith("La pieza resume hechos")
    assert any(
        "repair_object_text_extracted: rationale" == warning for warning in result.repair_warnings
    )
    assert any("repair_regularized_nested_tone" in warning for warning in result.repair_warnings)


def test_normalize_editorial_payload_truncates_overlong_evidence_lists_deterministically() -> None:
    result = normalize_editorial_payload(
        {
            "article_type": "analysis",
            "bias_label": "unclear",
            "evidence_spans": [f"evidence span {idx}" for idx in range(1, 10)],
            "framing_devices": [{"description": "public_safety"} for _ in range(10)],
            "rationale": {
                "description": (
                    "The output is broadly usable but the provider returned too many "
                    "supporting fragments."
                ),
            },
            "confidence": "moderate",
        }
    )

    assert result.truncated_fields == ("framing_devices", "evidence_spans")
    assert result.final_payload.evidence_spans[0].text == "evidence span 1"
    assert len(result.final_payload.evidence_spans) == 3
    assert "repair_data_loss" in result.unclear_reasons
    assert result.diagnostics.dimension_status["framing"].status == "resolved"
    assert any(
        "repair_truncated_evidence_spans: 9 -> 6" == warning for warning in result.repair_warnings
    )


def test_normalize_editorial_payload_marks_provider_missing_vs_weak_signal_vs_out_of_domain() -> (
    None
):
    weak_signal = normalize_editorial_payload(
        {
            "article_type": "explainer",
            "bias_label": "unclear",
            "evidence_spans": ["Claves para entender la reforma del mercado eléctrico"],
            "rationale": "Useful explainer with limited ideological signal and descriptive framing.",
        }
    )
    provider_missing = normalize_editorial_payload(
        {
            "article_type": "analysis",
            "evidence_spans": ["El texto describe posiciones enfrentadas sin definir una propia."],
            "rationale": "The provider omitted several dimensions entirely.",
        }
    )
    out_of_domain = normalize_editorial_payload(
        {
            "article_type": "news_report",
            "evidence_spans": ["El delantero marcó dos goles para cerrar la victoria."],
            "rationale": "Sports recap focused on match events rather than editorial framing.",
        }
    )

    assert weak_signal.diagnostics.dimension_status["bias"].status == "weak_signal_abstain"
    assert provider_missing.diagnostics.dimension_status["bias"].status == "provider_missing"
    assert out_of_domain.diagnostics.editorial_applicability == "out_of_domain"
    assert out_of_domain.diagnostics.dimension_status["bias"].status == "out_of_domain"


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
