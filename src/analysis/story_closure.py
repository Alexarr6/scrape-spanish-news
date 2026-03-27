"""Guarded story-cluster closure and component assembly helpers."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from src.analysis.contracts import StoryClusterMemberReason


@dataclass(slots=True)
class StoryClosureBuilder:
    high_recall_mode: bool = False

    def raw_connected_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    ) -> list[list[int]]:
        adjacency: dict[int, set[int]] = defaultdict(set)
        for left, right, _ in accepted_edges:
            adjacency[left].add(right)
            adjacency[right].add(left)

        remaining = set(article_ids)
        components: list[list[int]] = []
        while remaining:
            seed = remaining.pop()
            component = [seed]
            queue = deque([seed])
            while queue:
                node = queue.popleft()
                for neighbor in sorted(adjacency.get(node, set())):
                    if neighbor not in remaining:
                        continue
                    remaining.remove(neighbor)
                    component.append(neighbor)
                    queue.append(neighbor)
            components.append(sorted(component))
        return sorted(components, key=len, reverse=True)

    def build_guarded_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    ) -> tuple[list[list[int]], dict[int, dict[str, object]]]:
        strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
        medium_adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
        raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
        for left, right, reason in sorted(
            accepted_edges, key=lambda item: item[2].score, reverse=True
        ):
            edge_class = self.classify_closure_edge(reason)
            if edge_class == "discard":
                continue
            raw_adjacency[left][right] = reason
            raw_adjacency[right][left] = reason
            target = strong_adjacency if edge_class == "strong" else medium_adjacency
            target[left][right] = reason
            target[right][left] = reason

        remaining = set(article_ids)
        components: list[set[int]] = []
        member_meta: dict[int, dict[str, object]] = {}
        while remaining:
            seed = max(
                remaining,
                key=lambda article_id: max(
                    (
                        reason.score
                        for adjacency in (strong_adjacency, medium_adjacency)
                        for reason in adjacency.get(article_id, {}).values()
                    ),
                    default=0.0,
                ),
            )
            cluster = {seed}
            remaining.remove(seed)
            member_meta[seed] = {
                "closure_stage": "seed",
                "closure_decision": "seed",
                "closure_support_count": 0,
            }
            queue = deque([seed])
            while queue:
                node = queue.popleft()
                for neighbor in sorted(strong_adjacency.get(node, {})):
                    if neighbor not in remaining:
                        continue
                    remaining.remove(neighbor)
                    cluster.add(neighbor)
                    queue.append(neighbor)
                    support = [
                        strong_adjacency[neighbor][member]
                        for member in cluster
                        if member != neighbor and member in strong_adjacency.get(neighbor, {})
                    ]
                    member_meta[neighbor] = self.closure_attach_meta(
                        cluster_size=len(cluster),
                        support=support,
                        decision="strong_component",
                        stage="strong",
                    )
            components.append(cluster)

        self.preserve_medium_components(
            components=components,
            member_meta=member_meta,
            raw_adjacency=raw_adjacency,
            strong_adjacency=strong_adjacency,
        )
        self.merge_supported_components(
            components=components,
            member_meta=member_meta,
            strong_adjacency=strong_adjacency,
            medium_adjacency=medium_adjacency,
        )

        singleton_cluster_by_id = {
            next(iter(component)): component for component in components if len(component) == 1
        }
        candidate_singletons = sorted(singleton_cluster_by_id)
        for candidate in candidate_singletons:
            own_cluster = singleton_cluster_by_id.get(candidate)
            if own_cluster is None or len(own_cluster) != 1:
                continue
            best_target: set[int] | None = None
            best_support: list[StoryClusterMemberReason] = []
            best_decision: str | None = None
            for cluster in components:
                if cluster is own_cluster or not cluster:
                    continue
                support = [
                    adjacency[candidate][member]
                    for adjacency in (strong_adjacency, medium_adjacency)
                    for member in cluster
                    if member in adjacency.get(candidate, {})
                ]
                attach_decision = self.should_attach_candidate(cluster, support)
                if attach_decision is None:
                    continue
                if not best_support or max(
                    reason.score for reason in support
                ) > max(reason.score for reason in best_support):
                    best_target = cluster
                    best_support = support
                    best_decision = attach_decision
            if best_target is None or best_decision is None:
                member_meta[candidate] = {
                    "closure_stage": "singleton",
                    "closure_decision": "no_support",
                    "closure_support_count": 0,
                }
                continue
            best_target.add(candidate)
            own_cluster.clear()
            singleton_cluster_by_id.pop(candidate, None)
            member_meta[candidate] = self.closure_attach_meta(
                cluster_size=len(best_target),
                support=best_support,
                decision=best_decision,
                stage="attach",
            )
        if self.high_recall_mode:
            self.merge_supported_components(
                components=components,
                member_meta=member_meta,
                strong_adjacency=strong_adjacency,
                medium_adjacency=medium_adjacency,
            )

        final_components = [component for component in components if component]
        normalized = [sorted(component) for component in final_components]
        return sorted(normalized, key=len, reverse=True), member_meta

    def preserve_medium_components(
        self,
        *,
        components: list[set[int]],
        member_meta: dict[int, dict[str, object]],
        raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
        strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
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
            audit = self.audit_medium_component(
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
                member_meta[node] = self.closure_attach_meta(
                    cluster_size=len(new_cluster),
                    support=audit["support_by_node"].get(node, []),
                    decision="preserved_medium_component",
                    stage="medium_component",
                )
            components.append(new_cluster)

    def merge_supported_components(
        self,
        *,
        components: list[set[int]],
        member_meta: dict[int, dict[str, object]],
        strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
        medium_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
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
                    decision = self.should_merge_components(
                        left_cluster,
                        right_cluster,
                        support,
                    )
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
                member_meta[article_id] = self.closure_attach_meta(
                    cluster_size=cluster_size,
                    support=support,
                    decision=decision,
                    stage="merge",
                )
            changed = True

    def should_merge_components(
        self,
        left_cluster: set[int],
        right_cluster: set[int],
        support: list[StoryClusterMemberReason],
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
            self.high_recall_mode
            and len(support) >= 1
            and best.days_delta <= 3
            and best.shared_entity_count >= 2
            and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
            and best.score >= 0.5
        ):
            return "component_followup_bridge"
        if (
            self.high_recall_mode
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
            and self.classify_closure_edge(best) == "strong"
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

    def audit_medium_component(
        self,
        *,
        raw_component: list[int],
        raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
        strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
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
                if self.is_medium_component_edge_compatible(reason):
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
        if self.high_recall_mode:
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

    def is_medium_component_edge_compatible(self, reason: StoryClusterMemberReason) -> bool:
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
        return reason.score >= (0.5 if self.high_recall_mode else 0.54)

    def classify_closure_edge(self, reason: StoryClusterMemberReason) -> str:
        if reason.risky_bridge_pair and reason.score < 0.78:
            return "discard"
        if (
            self.high_recall_mode
            and not reason.risky_bridge_pair
            and reason.semantic_similarity >= 0.84
            and reason.days_delta <= 3
            and (reason.shared_tag_count >= 1 or reason.shared_keyphrase_count >= 1)
            and reason.score >= 0.52
            and not any(
                penalty
                in {"entity_glue_penalty", "late_story_drift_penalty", "secondary_form_penalty"}
                for penalty in reason.penalties
            )
        ):
            return "strong"
        clean_rewrite_edge = (
            not reason.risky_bridge_pair
            and reason.title_similarity >= (0.72 if self.high_recall_mode else 0.78)
            and reason.days_delta <= 3
            and (reason.shared_tag_count >= 1 or reason.shared_keyphrase_count >= 1)
            and reason.score >= (0.54 if self.high_recall_mode else 0.58)
            and not any(
                penalty
                in {"entity_glue_penalty", "late_story_drift_penalty", "secondary_form_penalty"}
                for penalty in reason.penalties
            )
        )
        if clean_rewrite_edge:
            return "strong"
        if not reason.risky_bridge_pair and reason.score >= 0.78:
            return "strong"
        return "medium"

    def closure_attach_meta(
        self,
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
        self,
        cluster: set[int],
        support: list[StoryClusterMemberReason],
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
            and best.title_similarity >= (0.72 if self.high_recall_mode else 0.78)
            and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
        )
        if len(cluster) == 1:
            return (
                "seed_pair"
                if (
                    best_score >= (0.52 if self.high_recall_mode else 0.56)
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
        if clean_rewrite_attach and best_score >= (0.5 if self.high_recall_mode else 0.54):
            return "clean_rewrite_attach"
        if clean_rewrite_attach and support_count >= 2 and mean_score >= 0.5:
            return "rewrite_multi_support_attach"
        if (
            self.high_recall_mode
            and not risky_support
            and best.semantic_similarity >= 0.82
            and best.days_delta <= 3
            and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
            and best_score >= 0.5
        ):
            return "semantic_single_support_attach"
        if (
            support_count >= 2
            and mean_score >= (0.52 if self.high_recall_mode else 0.56)
            and best_score >= (0.54 if self.high_recall_mode else 0.58)
            and not risky_support
        ):
            return "multi_support"
        pivot_compatible = (
            not best.risky_bridge_pair
            and best.days_delta <= 4
            and best_score >= (0.54 if self.high_recall_mode else 0.58)
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
