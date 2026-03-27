from __future__ import annotations

from src.analysis.readside.editorial_summary_parts.json_payloads import (
    parse_json_list,
    parse_json_object,
    parse_json_scalar_list,
)
from src.analysis.readside.editorial_summary_parts.review_flags import build_review_flags
from src.analysis.store.models import ArticleEditorialAnalysisORM


def shape_product_editorial_summary(
    article_id: int, analysis: ArticleEditorialAnalysisORM | None
) -> dict:
    if analysis is None:
        return {
            "article_id": article_id,
            "analysis_status": "pending",
            "editorial_applicability": "full",
            "editorial_applicability_reason": "general_editorial_content",
            "article_type": "unclear",
            "article_type_confidence": 0.0,
            "bias_label": "unclear",
            "bias_score": 0.0,
            "bias_confidence": 0.0,
            "tone_emotional": "unclear",
            "tone_target": "unclear",
            "opinionatedness": "unclear",
            "sensationalism": "unclear",
            "rhetorical_certainty": "unclear",
            "framing_devices": [],
            "evidence_spans": [],
            "rationale": "Editorial analysis pending.",
            "unclear_reasons": [],
            "review_flags": build_review_flags(
                analysis_status="pending",
                bias_label="unclear",
                bias_confidence=0.0,
                evidence_spans=[],
                unclear_reasons=[],
                editorial_applicability="full",
            ),
            "diagnostics_summary": None,
        }
    evidence_spans = parse_json_list(analysis.evidence_spans_json)
    unclear_reasons = parse_json_scalar_list(analysis.unclear_reasons_json)
    diagnostics = parse_json_object(analysis.diagnostics_json)
    return {
        "article_id": article_id,
        "analysis_status": analysis.analysis_status,
        "editorial_applicability": analysis.editorial_applicability,
        "editorial_applicability_reason": analysis.editorial_applicability_reason,
        "article_type": analysis.article_type,
        "article_type_confidence": float(analysis.article_type_confidence),
        "bias_label": analysis.bias_label,
        "bias_score": float(analysis.bias_score),
        "bias_confidence": float(analysis.bias_confidence),
        "tone_emotional": analysis.tone_emotional,
        "tone_target": analysis.tone_target,
        "opinionatedness": analysis.opinionatedness,
        "sensationalism": analysis.sensationalism,
        "rhetorical_certainty": analysis.rhetorical_certainty,
        "framing_devices": parse_json_scalar_list(analysis.framing_devices_json),
        "evidence_spans": [
            {
                "type": str(item.get("type") or item.get("kind") or "quote"),
                "text": str(item.get("text") or item.get("span") or ""),
                "note": str(item.get("note") or item.get("context") or ""),
            }
            for item in evidence_spans[:3]
            if isinstance(item, dict) and (item.get("text") or item.get("span"))
        ],
        "rationale": analysis.rationale or "",
        "unclear_reasons": unclear_reasons,
        "review_flags": build_review_flags(
            analysis_status=analysis.analysis_status,
            bias_label=analysis.bias_label,
            bias_confidence=float(analysis.bias_confidence),
            evidence_spans=evidence_spans,
            unclear_reasons=unclear_reasons,
            editorial_applicability=analysis.editorial_applicability,
        ),
        "diagnostics_summary": {
            "dimension_status": {
                key: value
                for key, value in {
                    "article_type": analysis.article_type_status,
                    "bias": analysis.bias_status,
                    "tone_emotional": analysis.tone_emotional_status,
                    "tone_target": analysis.tone_target_status,
                    "opinionatedness": analysis.opinionatedness_status,
                    "sensationalism": analysis.sensationalism_status,
                    "rhetorical_certainty": analysis.rhetorical_certainty_status,
                    "framing": analysis.framing_status,
                }.items()
                if value
            }
        }
        if diagnostics or any(
            [
                analysis.article_type_status,
                analysis.bias_status,
                analysis.tone_emotional_status,
                analysis.tone_target_status,
                analysis.opinionatedness_status,
                analysis.sensationalism_status,
                analysis.rhetorical_certainty_status,
                analysis.framing_status,
            ]
        )
        else None,
    }


def shape_member_editorial_preview(analysis: ArticleEditorialAnalysisORM | None) -> dict:
    summary = shape_product_editorial_summary(getattr(analysis, "article_id", 0), analysis)
    return {
        "analysis_status": summary["analysis_status"],
        "article_type": summary["article_type"],
        "article_type_confidence": summary["article_type_confidence"],
        "bias_label": summary["bias_label"],
        "bias_confidence": summary["bias_confidence"],
        "editorial_applicability": summary["editorial_applicability"],
        "review_flags": {
            "low_confidence": summary["review_flags"]["low_confidence"],
            "needs_review": summary["review_flags"]["needs_review"],
            "unclear_bias": summary["review_flags"]["unclear_bias"],
            "out_of_domain": summary["review_flags"]["out_of_domain"],
            "pending_analysis": summary["review_flags"]["pending_analysis"],
        },
    }
