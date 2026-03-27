"""Guarded story-cluster closure and component assembly helpers."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from src.analysis.clustering.closure_parts.attachments import (
    closure_attach_meta,
    should_attach_candidate,
)
from src.analysis.clustering.closure_parts.graphs import (
    build_closure_adjacency,
    raw_connected_components,
)
from src.analysis.clustering.closure_parts.merge_policy import (
    audit_medium_component,
    classify_closure_edge,
    is_medium_component_edge_compatible,
    merge_supported_components,
    preserve_medium_components,
    should_merge_components,
)
from src.analysis.shared.contracts import StoryClusterMemberReason


@dataclass(slots=True)
class StoryClosureBuilder:
    high_recall_mode: bool = False

    def raw_connected_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    ) -> list[list[int]]:
        return raw_connected_components(article_ids, accepted_edges)

    def build_guarded_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    ) -> tuple[list[list[int]], dict[int, dict[str, object]]]:
        strong_adjacency, medium_adjacency, raw_adjacency = build_closure_adjacency(
            accepted_edges,
            classify_edge=self.classify_closure_edge,
        )

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
        preserve_medium_components(
            components=components,
            member_meta=member_meta,
            raw_adjacency=raw_adjacency,
            strong_adjacency=strong_adjacency,
            attach_meta=self.closure_attach_meta,
            audit_component=self.audit_medium_component,
        )

    def merge_supported_components(
        self,
        *,
        components: list[set[int]],
        member_meta: dict[int, dict[str, object]],
        strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
        medium_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    ) -> None:
        merge_supported_components(
            components=components,
            member_meta=member_meta,
            strong_adjacency=strong_adjacency,
            medium_adjacency=medium_adjacency,
            attach_meta=self.closure_attach_meta,
            merge_decision=self.should_merge_components,
        )

    def should_merge_components(
        self,
        left_cluster: set[int],
        right_cluster: set[int],
        support: list[StoryClusterMemberReason],
    ) -> str | None:
        return should_merge_components(
            left_cluster,
            right_cluster,
            support,
            high_recall_mode=self.high_recall_mode,
            classify_edge=self.classify_closure_edge,
        )

    def audit_medium_component(
        self,
        *,
        raw_component: list[int],
        raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
        strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    ) -> dict[str, object]:
        return audit_medium_component(
            raw_component=raw_component,
            raw_adjacency=raw_adjacency,
            strong_adjacency=strong_adjacency,
            high_recall_mode=self.high_recall_mode,
            is_edge_compatible=self.is_medium_component_edge_compatible,
        )

    def is_medium_component_edge_compatible(self, reason: StoryClusterMemberReason) -> bool:
        return is_medium_component_edge_compatible(reason, high_recall_mode=self.high_recall_mode)

    def classify_closure_edge(self, reason: StoryClusterMemberReason) -> str:
        return classify_closure_edge(reason, high_recall_mode=self.high_recall_mode)

    def closure_attach_meta(
        self,
        *,
        cluster_size: int,
        support: list[StoryClusterMemberReason],
        decision: str,
        stage: str,
    ) -> dict[str, object]:
        return closure_attach_meta(
            cluster_size=cluster_size,
            support=support,
            decision=decision,
            stage=stage,
        )

    def should_attach_candidate(
        self,
        cluster: set[int],
        support: list[StoryClusterMemberReason],
    ) -> str | None:
        return should_attach_candidate(
            cluster,
            support,
            high_recall_mode=self.high_recall_mode,
        )
