from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

import numpy as np
from sklearn.cluster import HDBSCAN

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
    min_cluster_size: int = 3
    min_samples: int = 2
    neighbor_k: int = 4
    cluster_selection_epsilon: float = 0.0


def analyze_points(
    points: list[PointArtifact],
    embeddings: list[EmbeddingArtifact],
    *,
    config: AnalysisConfig | None = None,
) -> SemanticAnalysisArtifact:
    config = config or AnalysisConfig()
    metadata = AnalysisMetadataArtifact(
        distance_basis="normalized_embedding_euclidean",
        article_ids=sorted(point.article_id for point in points),
        article_count=len(points),
        config=asdict(config) | {"algorithm": "hdbscan"},
    )
    if not points:
        return SemanticAnalysisArtifact(
            points=[], clusters=[], unclustered_article_ids=[], metadata=metadata
        )

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

    ordered_ids = [point.article_id for point in points]
    matrix = np.array([embeddings_by_id[article_id].embedding for article_id in ordered_ids], dtype=float)
    if matrix.ndim != 2:
        raise ValueError("semantic analysis requires a 2D embedding matrix")
    normalized = _normalize_rows(matrix)
    distance_matrix = _pairwise_distance_matrix(normalized)
    local_density = _local_density_scores(distance_matrix, neighbor_k=min(config.neighbor_k, max(len(points) - 1, 1)))
    nearby_sources = {
        article_id: _nearby_sources_for_index(
            index=index,
            ordered_ids=ordered_ids,
            points_by_id=points_by_id,
            distance_matrix=distance_matrix,
            neighbor_k=min(config.neighbor_k, max(len(points) - 1, 1)),
        )
        for index, article_id in enumerate(ordered_ids)
    }

    if len(points) == 1:
        metadata.thresholds = {"density_baseline": 0.0}
        return SemanticAnalysisArtifact(
            points=[
                PointAnalysisArtifact(
                    article_id=ordered_ids[0],
                    cluster_id=None,
                    cluster_size=0,
                    is_outlier=True,
                    local_density_distance=0.0,
                    source_neighbor_diversity=1,
                    nearby_sources=nearby_sources[ordered_ids[0]],
                )
            ],
            clusters=[],
            unclustered_article_ids=[ordered_ids[0]],
            density_baseline=0.0,
            outlier_count=1,
            metadata=metadata,
        )

    labels = _cluster_labels(normalized, config=config)
    cluster_sizes = Counter(label for label in labels if label >= 0)
    cluster_ids = {label: index + 1 for index, label in enumerate(sorted(cluster_sizes))}
    metadata.thresholds = {
        "density_baseline": round(float(np.median(local_density)) if local_density.size else 0.0, 6),
        "min_cluster_size": float(config.min_cluster_size),
        "min_samples": float(config.min_samples),
    }

    analysis_points: list[PointAnalysisArtifact] = []
    clusters: list[ClusterArtifact] = []
    cluster_members: dict[int, list[int]] = {}
    for article_id, raw_label in zip(ordered_ids, labels, strict=True):
        if raw_label >= 0:
            cluster_members.setdefault(cluster_ids[raw_label], []).append(article_id)

    for cluster_id, member_ids in sorted(cluster_members.items()):
        member_points = [points_by_id[article_id] for article_id in sorted(member_ids)]
        member_sources = Counter(point.source for point in member_points)
        representative_ids = [point.article_id for point in member_points[:3]]
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
                centroid_z=sum(point.z for point in member_points) / len(member_points),
            )
        )

    for index, article_id in enumerate(ordered_ids):
        raw_label = labels[index]
        cluster_id = cluster_ids.get(raw_label) if raw_label >= 0 else None
        cluster_size = cluster_sizes.get(raw_label, 0) if raw_label >= 0 else 0
        sources = nearby_sources[article_id]
        analysis_points.append(
            PointAnalysisArtifact(
                article_id=article_id,
                cluster_id=cluster_id,
                cluster_size=cluster_size,
                is_outlier=bool(raw_label < 0),
                local_density_distance=round(float(local_density[index]), 6),
                source_neighbor_diversity=len(sources),
                nearby_sources=sources,
            )
        )

    unclustered = sorted(article_id for article_id, raw_label in zip(ordered_ids, labels, strict=True) if raw_label < 0)
    return SemanticAnalysisArtifact(
        points=analysis_points,
        clusters=clusters,
        unclustered_article_ids=unclustered,
        density_baseline=metadata.thresholds["density_baseline"],
        outlier_count=len(unclustered),
        metadata=metadata,
    )


def _cluster_labels(normalized_embeddings: np.ndarray, *, config: AnalysisConfig) -> np.ndarray:
    if len(normalized_embeddings) < config.min_cluster_size:
        return np.full(len(normalized_embeddings), -1, dtype=int)
    estimator = HDBSCAN(
        min_cluster_size=max(2, config.min_cluster_size),
        min_samples=max(1, min(config.min_samples, len(normalized_embeddings) - 1)),
        cluster_selection_epsilon=config.cluster_selection_epsilon,
        metric="euclidean",
        allow_single_cluster=False,
        copy=False,
    )
    return estimator.fit_predict(normalized_embeddings)


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("semantic analysis cannot use zero-length embedding vectors")
    return matrix / norms


def _pairwise_distance_matrix(normalized_embeddings: np.ndarray) -> np.ndarray:
    diff = normalized_embeddings[:, None, :] - normalized_embeddings[None, :, :]
    return np.sqrt(np.sum(diff * diff, axis=2))


def _local_density_scores(distance_matrix: np.ndarray, *, neighbor_k: int) -> np.ndarray:
    if len(distance_matrix) <= 1:
        return np.zeros(len(distance_matrix), dtype=float)
    scores = []
    for index in range(len(distance_matrix)):
        row = np.delete(distance_matrix[index], index)
        nearest = np.sort(row)[:neighbor_k]
        scores.append(float(np.mean(nearest)))
    return np.array(scores, dtype=float)


def _nearby_sources_for_index(
    *,
    index: int,
    ordered_ids: list[int],
    points_by_id: dict[int, PointArtifact],
    distance_matrix: np.ndarray,
    neighbor_k: int,
) -> list[str]:
    if len(ordered_ids) == 1:
        return [points_by_id[ordered_ids[0]].source]
    distances = [
        (distance_matrix[index, candidate_index], ordered_ids[candidate_index])
        for candidate_index in range(len(ordered_ids))
        if candidate_index != index
    ]
    nearest_ids = [article_id for _distance, article_id in sorted(distances)[:neighbor_k]]
    sources = {points_by_id[ordered_ids[index]].source}
    sources.update(points_by_id[article_id].source for article_id in nearest_ids)
    return sorted(sources)
