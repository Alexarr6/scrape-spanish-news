from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from statistics import median

from src.semantic.contracts import (
    AnalysisMetadataArtifact,
    ClusterArtifact,
    EmbeddingArtifact,
    PointAnalysisArtifact,
    PointArtifact,
    SemanticAnalysisArtifact,
)


@dataclass(frozen=True)
class AnalysisConfig:
    neighbor_k: int = 4
    min_cluster_size: int = 3
    core_distance_scale: float = 1.15
    edge_distance_scale: float = 1.35
    attach_distance_scale: float = 1.6
    outlier_distance_scale: float = 1.3


@dataclass(frozen=True)
class _ClusterSeed:
    article_ids: list[int]
    median_density_distance: float


def analyze_points(
    points: list[PointArtifact],
    embeddings: list[EmbeddingArtifact],
    *,
    config: AnalysisConfig | None = None,
) -> SemanticAnalysisArtifact:
    config = config or AnalysisConfig()
    metadata = AnalysisMetadataArtifact(
        distance_basis="embedding_cosine_distance",
        article_ids=sorted(point.article_id for point in points),
        article_count=len(points),
        config=asdict(config),
    )
    if not points:
        return SemanticAnalysisArtifact(points=[], clusters=[], unclustered_article_ids=[], metadata=metadata)

    points_by_id = {point.article_id: point for point in points}
    embeddings_by_id = {embedding.article_id: embedding for embedding in embeddings}
    point_ids = set(points_by_id)
    embedding_ids = set(embeddings_by_id)
    if point_ids != embedding_ids:
        raise ValueError(
            "semantic analysis requires aligned article ids; "
            f"points_only={sorted(point_ids - embedding_ids)} "
            f"embeddings_only={sorted(embedding_ids - point_ids)}"
        )

    if len(points) == 1:
        point = points[0]
        metadata.thresholds = {
            "density_baseline": 0.0,
            "core_distance": 0.0,
            "outlier_distance": 0.0,
        }
        return SemanticAnalysisArtifact(
            points=[
                PointAnalysisArtifact(
                    article_id=point.article_id,
                    cluster_id=None,
                    cluster_size=0,
                    is_outlier=True,
                    local_density_distance=0.0,
                    source_neighbor_diversity=1,
                    nearby_sources=[point.source],
                )
            ],
            clusters=[],
            unclustered_article_ids=[point.article_id],
            metadata=metadata,
        )

    ordered_ids = [point.article_id for point in points]
    distance_map = _distance_matrix(ordered_ids, embeddings_by_id)
    neighbor_k = max(1, min(config.neighbor_k, len(points) - 1))
    local_density = {
        article_id: _mean_nearest_distance(article_id, ordered_ids, distance_map, neighbor_k)
        for article_id in ordered_ids
    }
    diversity = {
        article_id: _neighbor_source_summary(article_id, ordered_ids, points_by_id, distance_map, neighbor_k)
        for article_id in ordered_ids
    }

    density_values = list(local_density.values())
    density_baseline = max(median(density_values), 1e-9)
    core_threshold = density_baseline * config.core_distance_scale
    outlier_threshold = density_baseline * config.outlier_distance_scale
    metadata.thresholds = {
        "density_baseline": round(density_baseline, 6),
        "core_distance": round(core_threshold, 6),
        "outlier_distance": round(outlier_threshold, 6),
    }
    core_ids = {
        article_id
        for article_id, mean_distance in local_density.items()
        if mean_distance <= core_threshold
    }

    components = _connected_components(
        core_ids,
        ordered_ids,
        distance_map,
        local_density,
        scale=config.edge_distance_scale,
    )
    cluster_seeds = [
        _ClusterSeed(
            article_ids=component,
            median_density_distance=median(local_density[i] for i in component),
        )
        for component in components
        if len(component) >= config.min_cluster_size
    ]

    cluster_members: dict[int, set[int]] = {
        index + 1: set(seed.article_ids) for index, seed in enumerate(cluster_seeds)
    }
    assigned = {article_id for members in cluster_members.values() for article_id in members}

    for article_id in ordered_ids:
        if article_id in assigned:
            continue
        best_cluster_id: int | None = None
        best_distance: float | None = None
        for cluster_id, seed in enumerate(cluster_seeds, start=1):
            attach_limit = (
                max(seed.median_density_distance, density_baseline) * config.attach_distance_scale
            )
            distance_to_cluster = min(
                distance_map[(article_id, member_id)]
                for member_id in seed.article_ids
                if member_id != article_id
            )
            if distance_to_cluster > attach_limit:
                continue
            if best_distance is None or distance_to_cluster < best_distance:
                best_cluster_id = cluster_id
                best_distance = distance_to_cluster
        if best_cluster_id is not None:
            cluster_members[best_cluster_id].add(article_id)
            assigned.add(article_id)

    analysis_points: list[PointAnalysisArtifact] = []
    cluster_lookup = {
        article_id: cluster_id
        for cluster_id, members in cluster_members.items()
        for article_id in members
    }
    clusters: list[ClusterArtifact] = []

    for cluster_id, member_ids in sorted(cluster_members.items()):
        member_points = [points_by_id[article_id] for article_id in sorted(member_ids)]
        member_sources = Counter(point.source for point in member_points)
        representative_ids = [point.article_id for point in sorted(member_points, key=lambda item: item.article_id)[:3]]
        clusters.append(
            ClusterArtifact(
                cluster_id=cluster_id,
                size=len(member_points),
                article_ids=sorted(member_ids),
                representative_article_ids=representative_ids,
                top_sources=dict(sorted(member_sources.items(), key=lambda item: (-item[1], item[0]))),
                source_count=len(member_sources),
                source_dominance=max(member_sources.values()) / len(member_points),
                date_min=min((point.published_date for point in member_points if point.published_date), default=""),
                date_max=max((point.published_date for point in member_points if point.published_date), default=""),
                centroid_x=sum(point.x for point in member_points) / len(member_points),
                centroid_y=sum(point.y for point in member_points) / len(member_points),
            )
        )

    for article_id in ordered_ids:
        point = points_by_id[article_id]
        nearby_sources = diversity[article_id]
        cluster_id = cluster_lookup.get(article_id)
        cluster_size = len(cluster_members[cluster_id]) if cluster_id is not None else 0
        is_outlier = cluster_id is None and local_density[article_id] >= outlier_threshold
        analysis_points.append(
            PointAnalysisArtifact(
                article_id=article_id,
                cluster_id=cluster_id,
                cluster_size=cluster_size,
                is_outlier=is_outlier,
                local_density_distance=round(local_density[article_id], 6),
                source_neighbor_diversity=len(nearby_sources),
                nearby_sources=nearby_sources,
            )
        )

    unclustered = sorted(article_id for article_id in ordered_ids if article_id not in cluster_lookup)
    return SemanticAnalysisArtifact(
        points=analysis_points,
        clusters=clusters,
        unclustered_article_ids=unclustered,
        density_baseline=round(density_baseline, 6),
        outlier_count=sum(1 for point in analysis_points if point.is_outlier),
        metadata=metadata,
    )


def _distance_matrix(
    article_ids: list[int], embeddings_by_id: dict[int, EmbeddingArtifact]
) -> dict[tuple[int, int], float]:
    matrix: dict[tuple[int, int], float] = {}
    for left_id in article_ids:
        for right_id in article_ids:
            if left_id == right_id:
                matrix[(left_id, right_id)] = 0.0
                continue
            matrix[(left_id, right_id)] = _cosine_distance(
                embeddings_by_id[left_id].embedding,
                embeddings_by_id[right_id].embedding,
            )
    return matrix


def _cosine_distance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError(
            f"embedding length mismatch in semantic analysis: {len(left)} != {len(right)}"
        )
    dot = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0.0 or right_norm == 0.0:
        raise ValueError("semantic analysis cannot use zero-length embedding vectors")
    similarity = dot / (left_norm * right_norm)
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


def _sorted_neighbor_ids(
    article_id: int, ids: list[int], distance_map: dict[tuple[int, int], float]
) -> list[int]:
    return sorted(
        [candidate_id for candidate_id in ids if candidate_id != article_id],
        key=lambda candidate_id: (distance_map[(article_id, candidate_id)], candidate_id),
    )


def _mean_nearest_distance(
    article_id: int,
    ids: list[int],
    distance_map: dict[tuple[int, int], float],
    neighbor_k: int,
) -> float:
    nearest = _sorted_neighbor_ids(article_id, ids, distance_map)[:neighbor_k]
    return sum(distance_map[(article_id, neighbor_id)] for neighbor_id in nearest) / len(nearest)


def _neighbor_source_summary(
    article_id: int,
    ids: list[int],
    points_by_id: dict[int, PointArtifact],
    distance_map: dict[tuple[int, int], float],
    neighbor_k: int,
) -> list[str]:
    nearest = _sorted_neighbor_ids(article_id, ids, distance_map)[:neighbor_k]
    sources = {points_by_id[article_id].source}
    for neighbor_id in nearest:
        sources.add(points_by_id[neighbor_id].source)
    return sorted(sources)


def _connected_components(
    core_ids: set[int],
    ids: list[int],
    distance_map: dict[tuple[int, int], float],
    local_density: dict[int, float],
    *,
    scale: float,
) -> list[list[int]]:
    remaining = set(core_ids)
    components: list[list[int]] = []
    while remaining:
        seed = min(remaining)
        stack = [seed]
        component: list[int] = []
        remaining.remove(seed)
        while stack:
            current = stack.pop()
            component.append(current)
            for candidate in ids:
                if candidate not in remaining:
                    continue
                max_distance = max(local_density[current], local_density[candidate]) * scale
                if distance_map[(current, candidate)] <= max_distance:
                    remaining.remove(candidate)
                    stack.append(candidate)
        components.append(sorted(component))
    return sorted(components, key=lambda component: (len(component), component), reverse=True)
