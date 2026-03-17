import pytest

from scripts.build_semantic_map import (
    _artifact_paths,
    _canonicalize_semantic_records,
    _summary_line,
)
from src.semantic.contracts import (
    AnalysisMetadataArtifact,
    ClusterArtifact,
    EmbeddingArtifact,
    PointAnalysisArtifact,
    PointArtifact,
    SemanticAnalysisArtifact,
    SemanticBuildConfig,
)


def test_artifact_paths_include_analysis_json() -> None:
    config = SemanticBuildConfig(database_url="postgresql://example", stamp="20260317-190000")

    artifacts = _artifact_paths(config)

    assert artifacts["analysis_json"].endswith("semantic_analysis_20260317-190000.json")
    assert artifacts["points_json"].endswith("articles_points_20260317-190000.json")


def test_summary_line_reports_cluster_and_outlier_counts() -> None:
    points = [
        PointArtifact(article_id=1, source="elpais", title="A", url="https://e/1", published_at="")
    ]
    analysis = SemanticAnalysisArtifact(
        points=[PointAnalysisArtifact(article_id=1, cluster_id=2, cluster_size=4)],
        clusters=[ClusterArtifact(cluster_id=2, size=4)],
        outlier_count=1,
        metadata=AnalysisMetadataArtifact(article_ids=[1], article_count=1),
    )

    summary = _summary_line(points, analysis, "pca_2d_latest", html=True)

    assert "clusters=1" in summary
    assert "largest_cluster=4" in summary
    assert "outliers=1" in summary
    assert "html=yes" in summary


def test_canonicalize_semantic_records_uses_point_order_for_shared_ids() -> None:
    embeddings = [
        EmbeddingArtifact(
            article_id=2,
            source="b",
            title="B",
            url="https://e/2",
            published_at="",
            section="",
            summary_snippet="",
            text_length=1,
            embedding_model="test",
            embedding=[0.0, 1.0],
        ),
        EmbeddingArtifact(
            article_id=1,
            source="a",
            title="A",
            url="https://e/1",
            published_at="",
            section="",
            summary_snippet="",
            text_length=1,
            embedding_model="test",
            embedding=[1.0, 0.0],
        ),
    ]
    points = [
        PointArtifact(article_id=1, source="a", title="A", url="https://e/1", published_at=""),
        PointArtifact(article_id=2, source="b", title="B", url="https://e/2", published_at=""),
    ]

    aligned_embeddings, aligned_points = _canonicalize_semantic_records(
        embeddings,
        points,
        limit=1,
        projection_set="pca_2d_latest",
    )

    assert [record.article_id for record in aligned_points] == [1]
    assert [record.article_id for record in aligned_embeddings] == [1]


def test_canonicalize_semantic_records_rejects_drift() -> None:
    embeddings = [
        EmbeddingArtifact(
            article_id=1,
            source="a",
            title="A",
            url="https://e/1",
            published_at="",
            section="",
            summary_snippet="",
            text_length=1,
            embedding_model="test",
            embedding=[1.0, 0.0],
        )
    ]
    points = [
        PointArtifact(article_id=1, source="a", title="A", url="https://e/1", published_at=""),
        PointArtifact(article_id=2, source="b", title="B", url="https://e/2", published_at=""),
    ]

    with pytest.raises(RuntimeError, match="drift"):
        _canonicalize_semantic_records(
            embeddings,
            points,
            limit=10,
            projection_set="pca_2d_latest",
        )
