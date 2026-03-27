from __future__ import annotations

from collections import defaultdict, deque

from src.analysis.shared.contracts import StoryClusterMemberReason


def raw_connected_components(
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


def build_closure_adjacency(
    accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    *,
    classify_edge,
) -> tuple[
    dict[int, dict[int, StoryClusterMemberReason]],
    dict[int, dict[int, StoryClusterMemberReason]],
    dict[int, dict[int, StoryClusterMemberReason]],
]:
    strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
    medium_adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
    raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
    for left, right, reason in sorted(accepted_edges, key=lambda item: item[2].score, reverse=True):
        edge_class = classify_edge(reason)
        if edge_class == "discard":
            continue
        raw_adjacency[left][right] = reason
        raw_adjacency[right][left] = reason
        target = strong_adjacency if edge_class == "strong" else medium_adjacency
        target[left][right] = reason
        target[right][left] = reason
    return strong_adjacency, medium_adjacency, raw_adjacency
