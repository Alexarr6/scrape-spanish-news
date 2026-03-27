from __future__ import annotations

from collections import defaultdict, deque

from src.analysis.shared.contracts import StoryClusterMemberReason


def classify_closure_edge(reason: StoryClusterMemberReason, *, high_recall_mode: bool) -> str:
    if reason.risky_bridge_pair and reason.score < 0.78:
        return "discard"
    if (
        high_recall_mode
        and not reason.risky_bridge_pair
        and reason.semantic_similarity >= 0.84
        and reason.days_delta <= 3
        and (reason.shared_tag_count >= 1 or reason.shared_keyphrase_count >= 1)
        and reason.score >= 0.52
        and not any(
            penalty in {"entity_glue_penalty", "late_story_drift_penalty", "secondary_form_penalty"}
            for penalty in reason.penalties
        )
    ):
        return "strong"
    clean_rewrite_edge = (
        not reason.risky_bridge_pair
        and reason.title_similarity >= (0.72 if high_recall_mode else 0.78)
        and reason.days_delta <= 3
        and (reason.shared_tag_count >= 1 or reason.shared_keyphrase_count >= 1)
        and reason.score >= (0.54 if high_recall_mode else 0.58)
        and not any(
            penalty in {"entity_glue_penalty", "late_story_drift_penalty", "secondary_form_penalty"}
            for penalty in reason.penalties
        )
    )
    if clean_rewrite_edge:
        return "strong"
    if not reason.risky_bridge_pair and reason.score >= 0.78:
        return "strong"
    return "medium"


def should_merge_components(
    left_cluster: set[int],
    right_cluster: set[int],
    support: list[StoryClusterMemberReason],
    *,
    high_recall_mode: bool,
    classify_edge,
) -> str | None:
    if not support:
        return None
    best = max(support, key=lambda reason: reason.score)
    mean_score = sum(reason.score for reason in support) / len(support)
    if any(reason.risky_bridge_pair for reason in support):
        return None
    if any(reason.article_type_pair_class == "secondary_form_pair" for reason in support):
        return None
    if any(
        penalty in {"entity_glue_penalty", "late_story_drift_penalty", "secondary_form_penalty"}
        for reason in support
        for penalty in reason.penalties
    ):
        return None
    if best.days_delta > 3:
        return None
    if (
        high_recall_mode
        and len(support) >= 1
        and best.days_delta <= 3
        and best.shared_entity_count >= 2
        and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
        and best.score >= 0.5
    ):
        return "component_followup_bridge"
    if (
        high_recall_mode
        and best.semantic_similarity >= 0.82
        and best.days_delta <= 3
        and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
        and best.score >= 0.5
    ):
        return "component_semantic_bridge"
    if len(support) >= 2 and mean_score >= 0.52 and best.score >= 0.56:
        return "component_multi_support"
    if (
        len(left_cluster) >= 2
        and len(right_cluster) >= 2
        and classify_edge(best) == "strong"
        and best.score >= 0.56
    ):
        return "component_strong_bridge"
    clean_rewrite_bridge = (
        best.title_similarity >= 0.78
        and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
        and best.score >= 0.54
    )
    if clean_rewrite_bridge:
        return "component_rewrite_bridge"
    return None


def is_medium_component_edge_compatible(
    reason: StoryClusterMemberReason, *, high_recall_mode: bool
) -> bool:
    if reason.risky_bridge_pair:
        return False
    if reason.article_type_pair_class == "secondary_form_pair":
        return False
    forbidden_penalties = {
        "entity_glue_penalty",
        "late_story_drift_penalty",
        "secondary_form_penalty",
    }
    if any(penalty in forbidden_penalties for penalty in reason.penalties):
        return False
    if reason.days_delta > 3:
        return False
    if (
        reason.shared_entity_count < 2
        and reason.shared_tag_count < 1
        and reason.shared_keyphrase_count < 1
    ):
        return False
    if reason.shared_tag_count < 1 and reason.shared_keyphrase_count < 1:
        return False
    return reason.score >= (0.5 if high_recall_mode else 0.54)


def audit_medium_component(
    *,
    raw_component: list[int],
    raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    high_recall_mode: bool,
    is_edge_compatible,
) -> dict[str, object]:
    component_size = len(raw_component)
    if component_size < 2 or component_size > 5:
        return {"preserve": False}
    if any(strong_adjacency.get(node, {}) for node in raw_component):
        return {"preserve": False}

    support_by_node: dict[int, list[StoryClusterMemberReason]] = defaultdict(list)
    edges: list[StoryClusterMemberReason] = []
    compatible_edge_count = 0
    non_entity_signal_count = 0
    max_days_delta = 0
    for index, left in enumerate(raw_component):
        for right in raw_component[index + 1 :]:
            reason = raw_adjacency.get(left, {}).get(right)
            if reason is None:
                continue
            edges.append(reason)
            support_by_node[left].append(reason)
            support_by_node[right].append(reason)
            max_days_delta = max(max_days_delta, reason.days_delta)
            if reason.shared_tag_count >= 1 or reason.shared_keyphrase_count >= 1:
                non_entity_signal_count += 1
            if is_edge_compatible(reason):
                compatible_edge_count += 1
    minimum_edges = 1 if component_size == 2 else 2
    if len(edges) < minimum_edges:
        return {"preserve": False}
    if compatible_edge_count != len(edges):
        return {"preserve": False}
    if non_entity_signal_count < 1:
        return {"preserve": False}
    if max_days_delta > 3:
        return {"preserve": False}
    mean_score = sum(reason.score for reason in edges) / len(edges)
    best_score = max(reason.score for reason in edges)
    if high_recall_mode:
        minimum_mean = 0.5
        minimum_best = 0.52
    elif component_size <= 3:
        minimum_mean = 0.54
        minimum_best = 0.56
    else:
        minimum_mean = 0.55
        minimum_best = 0.56
    if mean_score < minimum_mean or best_score < minimum_best:
        return {"preserve": False}
    return {
        "preserve": True,
        "support_by_node": dict(support_by_node),
    }


def preserve_medium_components(
    *,
    components: list[set[int]],
    member_meta: dict[int, dict[str, object]],
    raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    attach_meta,
    audit_component,
) -> None:
    singleton_cluster_by_id = {
        next(iter(component)): component for component in components if len(component) == 1
    }
    visited: set[int] = set()
    for article_id in sorted(raw_adjacency):
        if article_id in visited or article_id not in singleton_cluster_by_id:
            continue
        raw_component = []
        queue = deque([article_id])
        visited.add(article_id)
        while queue:
            node = queue.popleft()
            raw_component.append(node)
            for neighbor in sorted(raw_adjacency.get(node, {})):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)
        raw_component = sorted(raw_component)
        if not all(node in singleton_cluster_by_id for node in raw_component):
            continue
        audit = audit_component(
            raw_component=raw_component,
            raw_adjacency=raw_adjacency,
            strong_adjacency=strong_adjacency,
        )
        if not audit["preserve"]:
            continue
        new_cluster = {node for node in raw_component}
        for node in raw_component:
            singleton_cluster_by_id[node].clear()
            singleton_cluster_by_id.pop(node, None)
            member_meta[node] = attach_meta(
                cluster_size=len(new_cluster),
                support=audit["support_by_node"].get(node, []),
                decision="preserved_medium_component",
                stage="medium_component",
            )
        components.append(new_cluster)


def merge_supported_components(
    *,
    components: list[set[int]],
    member_meta: dict[int, dict[str, object]],
    strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    medium_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    attach_meta,
    merge_decision,
) -> None:
    changed = True
    while changed:
        changed = False
        best_pair: tuple[int, int, list[StoryClusterMemberReason], str] | None = None
        for left_index, left_cluster in enumerate(components):
            if not left_cluster:
                continue
            for right_index in range(left_index + 1, len(components)):
                right_cluster = components[right_index]
                if not right_cluster:
                    continue
                support = [
                    adjacency[left_id][right_id]
                    for adjacency in (strong_adjacency, medium_adjacency)
                    for left_id in left_cluster
                    for right_id in right_cluster
                    if right_id in adjacency.get(left_id, {})
                ]
                decision = merge_decision(left_cluster, right_cluster, support)
                if decision is None:
                    continue
                if best_pair is None or max(reason.score for reason in support) > max(
                    reason.score for reason in best_pair[2]
                ):
                    best_pair = (left_index, right_index, support, decision)
        if best_pair is None:
            break
        left_index, right_index, support, decision = best_pair
        left_cluster = components[left_index]
        right_cluster = components[right_index]
        left_cluster.update(right_cluster)
        right_cluster.clear()
        cluster_size = len(left_cluster)
        for article_id in left_cluster:
            member_meta[article_id] = attach_meta(
                cluster_size=cluster_size,
                support=support,
                decision=decision,
                stage="merge",
            )
        changed = True
