from __future__ import annotations

import math

import numpy as np
from sklearn.decomposition import PCA

from src.semantic.contracts import EmbeddingArtifact, PointArtifact


def project_embeddings(
    records: list[EmbeddingArtifact], *, dimensions: int = 3
) -> list[PointArtifact]:
    if not records:
        return []
    if dimensions not in {2, 3}:
        raise ValueError("projection dimensions must be 2 or 3")

    matrix = np.array([record.embedding for record in records], dtype=float)
    component_count = min(dimensions, len(records), matrix.shape[1])
    if component_count <= 0:
        coords = np.zeros((len(records), dimensions), dtype=float)
    elif len(records) == 1:
        coords = np.zeros((1, dimensions), dtype=float)
    else:
        pca = PCA(n_components=component_count)
        projected = pca.fit_transform(matrix)
        coords = np.zeros((len(records), dimensions), dtype=float)
        coords[:, :component_count] = projected

    if len(records) > 0:
        centered = coords - coords.mean(axis=0, keepdims=True)
        max_abs = float(np.max(np.abs(centered)))
        coords = centered if max_abs <= 0 else centered / max_abs

    points: list[PointArtifact] = []
    for record, values in zip(records, coords, strict=True):
        x, y = float(values[0]), float(values[1])
        z = float(values[2]) if dimensions == 3 else 0.0
        if not all(math.isfinite(value) for value in (x, y, z)):
            raise ValueError("projection produced non-finite coordinates")
        points.append(
            PointArtifact(
                article_id=record.article_id,
                source=record.source,
                title=record.title,
                url=record.url,
                published_at=record.published_at,
                published_date=record.published_at[:10] if record.published_at else "",
                display_date=record.published_at[:10] if record.published_at else "",
                section=record.section,
                summary_snippet=record.summary_snippet,
                text_length=record.text_length,
                embedding_model=record.embedding_model,
                x=x,
                y=y,
                z=z,
            )
        )
    return points
