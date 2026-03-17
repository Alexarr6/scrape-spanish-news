from __future__ import annotations

import math

import numpy as np
from sklearn.decomposition import PCA

from src.semantic.contracts import EmbeddingArtifact, PointArtifact


def project_embeddings(records: list[EmbeddingArtifact]) -> list[PointArtifact]:
    if not records:
        return []

    matrix = np.array([record.embedding for record in records], dtype=float)
    if len(records) == 1:
        coords = np.array([[0.0, 0.0]], dtype=float)
    else:
        pca = PCA(n_components=2)
        coords = pca.fit_transform(matrix)

    points: list[PointArtifact] = []
    for record, (x, y) in zip(records, coords, strict=True):
        if not math.isfinite(float(x)) or not math.isfinite(float(y)):
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
                x=float(x),
                y=float(y),
            )
        )
    return points
