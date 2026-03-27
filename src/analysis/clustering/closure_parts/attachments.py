from __future__ import annotations

from src.analysis.shared.contracts import StoryClusterMemberReason


def closure_attach_meta(
    *,
    cluster_size: int,
    support: list[StoryClusterMemberReason],
    decision: str,
    stage: str,
) -> dict[str, object]:
    if not support:
        return {
            "closure_stage": stage,
            "closure_decision": decision,
            "closure_support_count": 0,
            "closure_cluster_size": cluster_size,
        }
    best = max(support, key=lambda reason: reason.score)
    return {
        "closure_stage": stage,
        "closure_decision": decision,
        "closure_support_count": len(support),
        "closure_cluster_size": cluster_size,
        "closure_best_score": round(best.score, 4),
        "closure_mean_score": round(sum(reason.score for reason in support) / len(support), 4),
        "closure_best_days_delta": best.days_delta,
        "closure_best_shared_entities": best.shared_entity_count,
        "closure_best_shared_tags": best.shared_tag_count,
        "closure_best_shared_keyphrases": best.shared_keyphrase_count,
        "closure_best_penalties": list(best.penalties),
    }


def should_attach_candidate(
    cluster: set[int],
    support: list[StoryClusterMemberReason],
    *,
    high_recall_mode: bool,
) -> str | None:
    if not support:
        return None
    best = max(support, key=lambda reason: reason.score)
    best_score = best.score
    support_count = len(support)
    mean_score = sum(reason.score for reason in support) / support_count
    risky_support = any(reason.risky_bridge_pair for reason in support)
    has_guardrail_penalty = any(
        penalty in {"entity_glue_penalty", "late_story_drift_penalty", "secondary_form_penalty"}
        for reason in support
        for penalty in reason.penalties
    )
    has_secondary_form = any(
        reason.article_type_pair_class == "secondary_form_pair" for reason in support
    )
    clean_followup_attach = (
        not risky_support
        and not has_secondary_form
        and not any(
            penalty in {"entity_glue_penalty", "late_story_drift_penalty"}
            for reason in support
            for penalty in reason.penalties
        )
        and best.days_delta <= 4
        and best.shared_entity_count >= 2
        and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
    )
    clean_rewrite_attach = (
        not risky_support
        and not has_secondary_form
        and not has_guardrail_penalty
        and best.days_delta <= 3
        and best.title_similarity >= (0.72 if high_recall_mode else 0.78)
        and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
    )
    if len(cluster) == 1:
        return (
            "seed_pair"
            if (
                best_score >= (0.52 if high_recall_mode else 0.56)
                and not risky_support
                and not has_guardrail_penalty
                and not has_secondary_form
                and best.days_delta <= 3
                and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
            )
            else None
        )
    if clean_followup_attach and best_score >= 0.56:
        return "followup_single_support"
    if clean_followup_attach and support_count >= 2 and mean_score >= 0.5:
        return "followup_multi_support"
    if clean_rewrite_attach and best_score >= (0.5 if high_recall_mode else 0.54):
        return "clean_rewrite_attach"
    if clean_rewrite_attach and support_count >= 2 and mean_score >= 0.5:
        return "rewrite_multi_support_attach"
    if (
        high_recall_mode
        and not risky_support
        and best.semantic_similarity >= 0.82
        and best.days_delta <= 3
        and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
        and best_score >= 0.5
    ):
        return "semantic_single_support_attach"
    if (
        support_count >= 2
        and mean_score >= (0.52 if high_recall_mode else 0.56)
        and best_score >= (0.54 if high_recall_mode else 0.58)
        and not risky_support
    ):
        return "multi_support"
    pivot_compatible = (
        not best.risky_bridge_pair
        and best.days_delta <= 4
        and best_score >= (0.54 if high_recall_mode else 0.58)
        and best.shared_entity_count >= 1
        and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
        and "entity_glue_penalty" not in best.penalties
        and "late_story_drift_penalty" not in best.penalties
    )
    if pivot_compatible:
        return "strong_pivot_attach"
    if best_score >= 0.82 and mean_score >= 0.76 and not risky_support:
        return "high_confidence_attach"
    return None
