import pytest

from src.semantic.analyze import analyze_points
from src.semantic.contracts import EmbeddingArtifact, PointArtifact

POINTS = [
    PointArtifact(
        article_id=1, source="elpais", title="A", url="https://e/1", published_at="", x=0.0, y=0.0
    ),
    PointArtifact(
        article_id=2,
        source="elmundo",
        title="B",
        url="https://e/2",
        published_at="",
        x=0.12,
        y=0.08,
    ),
    PointArtifact(
        article_id=3, source="abc", title="C", url="https://e/3", published_at="", x=0.18, y=-0.04
    ),
    PointArtifact(
        article_id=4, source="elpais", title="D", url="https://e/4", published_at="", x=5.0, y=5.0
    ),
    PointArtifact(
        article_id=5, source="eldiario", title="E", url="https://e/5", published_at="", x=5.1, y=5.0
    ),
    PointArtifact(
        article_id=6, source="abc", title="F", url="https://e/6", published_at="", x=5.05, y=5.15
    ),
    PointArtifact(
        article_id=7,
        source="lavanguardia",
        title="G",
        url="https://e/7",
        published_at="",
        x=11.0,
        y=11.0,
    ),
]

EMBEDDINGS = [
    EmbeddingArtifact(article_id=1, source="elpais", title="A", url="https://e/1", published_at="", section="", summary_snippet="", text_length=10, embedding_model="test", embedding=[1.0, 0.0, 0.0]),
    EmbeddingArtifact(article_id=2, source="elmundo", title="B", url="https://e/2", published_at="", section="", summary_snippet="", text_length=10, embedding_model="test", embedding=[0.99, 0.01, 0.0]),
    EmbeddingArtifact(article_id=3, source="abc", title="C", url="https://e/3", published_at="", section="", summary_snippet="", text_length=10, embedding_model="test", embedding=[0.98, -0.02, 0.0]),
    EmbeddingArtifact(article_id=4, source="elpais", title="D", url="https://e/4", published_at="", section="", summary_snippet="", text_length=10, embedding_model="test", embedding=[0.0, 1.0, 0.0]),
    EmbeddingArtifact(article_id=5, source="eldiario", title="E", url="https://e/5", published_at="", section="", summary_snippet="", text_length=10, embedding_model="test", embedding=[0.02, 0.99, 0.0]),
    EmbeddingArtifact(article_id=6, source="abc", title="F", url="https://e/6", published_at="", section="", summary_snippet="", text_length=10, embedding_model="test", embedding=[-0.01, 0.98, 0.0]),
    EmbeddingArtifact(article_id=7, source="lavanguardia", title="G", url="https://e/7", published_at="", section="", summary_snippet="", text_length=10, embedding_model="test", embedding=[0.0, 0.0, 1.0]),
]


def test_analyze_points_detects_clusters_and_outlier_from_embeddings() -> None:
    analysis = analyze_points(POINTS, EMBEDDINGS)

    point_by_id = {point.article_id: point for point in analysis.points}
    assert point_by_id[1].cluster_id is not None
    assert point_by_id[1].cluster_size == 3
    assert point_by_id[4].cluster_id is not None
    assert point_by_id[4].cluster_id != point_by_id[1].cluster_id
    assert point_by_id[7].cluster_id is None
    assert point_by_id[7].is_outlier is True
    assert analysis.outlier_count == 1
    assert sorted(cluster.size for cluster in analysis.clusters) == [3, 3]
    assert analysis.metadata.distance_basis == "embedding_cosine_distance"
    assert analysis.metadata.article_count == 7
    assert analysis.metadata.thresholds["density_baseline"] > 0


def test_analyze_points_ignores_misleading_2d_layout() -> None:
    misleading_points = [
        PointArtifact(article_id=1, source="elpais", title="A", url="https://e/1", published_at="", x=0.0, y=0.0),
        PointArtifact(article_id=2, source="elmundo", title="B", url="https://e/2", published_at="", x=10.0, y=10.0),
        PointArtifact(article_id=3, source="abc", title="C", url="https://e/3", published_at="", x=20.0, y=20.0),
        PointArtifact(article_id=4, source="elpais", title="D", url="https://e/4", published_at="", x=0.1, y=0.1),
        PointArtifact(article_id=5, source="eldiario", title="E", url="https://e/5", published_at="", x=10.1, y=10.1),
        PointArtifact(article_id=6, source="abc", title="F", url="https://e/6", published_at="", x=20.1, y=20.1),
    ]

    analysis = analyze_points(misleading_points, EMBEDDINGS[:6])
    point_by_id = {point.article_id: point for point in analysis.points}

    assert point_by_id[1].cluster_id == point_by_id[2].cluster_id == point_by_id[3].cluster_id
    assert point_by_id[4].cluster_id == point_by_id[5].cluster_id == point_by_id[6].cluster_id
    assert point_by_id[1].cluster_id != point_by_id[4].cluster_id


def test_analyze_points_rejects_misaligned_article_sets() -> None:
    with pytest.raises(ValueError, match="aligned article ids"):
        analyze_points(POINTS[:2], EMBEDDINGS[:1])


def test_analyze_points_summarizes_cross_source_mix() -> None:
    analysis = analyze_points(POINTS, EMBEDDINGS)

    first_cluster = analysis.clusters[0]
    assert first_cluster.source_count >= 2
    assert sum(first_cluster.top_sources.values()) == first_cluster.size

    point_by_id = {point.article_id: point for point in analysis.points}
    assert point_by_id[1].source_neighbor_diversity >= 2
    assert "elpais" in point_by_id[1].nearby_sources
