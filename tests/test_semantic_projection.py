import math

from src.semantic.contracts import EmbeddingArtifact
from src.semantic.project import project_embeddings


def _record(article_id: int, embedding: list[float]) -> EmbeddingArtifact:
    return EmbeddingArtifact(
        article_id=article_id,
        source="elpais",
        title=f"Article {article_id}",
        url=f"https://example.com/{article_id}",
        published_at="",
        section="",
        summary_snippet="",
        text_length=10,
        embedding_model="text-embedding-3-small",
        embedding=embedding,
    )


def test_project_embeddings_returns_finite_xyz_by_default() -> None:
    points = project_embeddings([
        _record(1, [1.0, 0.0, 0.0]),
        _record(2, [0.0, 1.0, 0.0]),
        _record(3, [0.0, 0.0, 1.0]),
    ])

    assert len(points) == 3
    assert all(math.isfinite(point.x) and math.isfinite(point.y) and math.isfinite(point.z) for point in points)
    assert len({point.z for point in points}) > 1


def test_project_embeddings_handles_single_row_in_3d() -> None:
    point = project_embeddings([_record(1, [0.4, 0.6, 0.8])])[0]
    assert point.x == 0.0
    assert point.y == 0.0
    assert point.z == 0.0


def test_project_embeddings_handles_two_rows_without_non_finite_z() -> None:
    points = project_embeddings([
        _record(1, [0.4, 0.6, 0.8]),
        _record(2, [0.1, 0.2, 0.3]),
    ])

    assert len(points) == 2
    assert all(math.isfinite(point.z) for point in points)


def test_project_embeddings_keeps_2d_projection_compatibility() -> None:
    points = project_embeddings(
        [
            _record(1, [1.0, 0.0, 0.0]),
            _record(2, [0.0, 1.0, 0.0]),
            _record(3, [0.0, 0.0, 1.0]),
        ],
        dimensions=2,
    )

    assert all(point.z == 0.0 for point in points)
