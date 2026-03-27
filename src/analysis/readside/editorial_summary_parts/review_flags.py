from __future__ import annotations


def build_review_flags(
    *,
    analysis_status: str,
    bias_label: str,
    bias_confidence: float,
    evidence_spans: list[dict],
    unclear_reasons: list[str],
    editorial_applicability: str,
) -> dict[str, bool]:
    missing_evidence = analysis_status == "completed" and not evidence_spans
    low_confidence = analysis_status == "completed" and bias_confidence < 0.45
    failed_analysis = analysis_status == "failed"
    unclear_bias = bias_label == "unclear"
    provider_missing = "provider_missing" in unclear_reasons
    mapping_loss = "mapping_loss" in unclear_reasons or "repair_data_loss" in unclear_reasons
    out_of_domain = editorial_applicability == "out_of_domain"
    pending_analysis = analysis_status == "pending"
    needs_review = any(
        [
            missing_evidence,
            low_confidence,
            failed_analysis,
            unclear_bias,
            provider_missing,
            mapping_loss,
            out_of_domain,
            pending_analysis,
        ]
    )
    return {
        "missing_evidence": missing_evidence,
        "low_confidence": low_confidence,
        "failed_analysis": failed_analysis,
        "unclear_bias": unclear_bias,
        "provider_missing": provider_missing,
        "mapping_loss": mapping_loss,
        "out_of_domain": out_of_domain,
        "pending_analysis": pending_analysis,
        "needs_review": needs_review,
    }
