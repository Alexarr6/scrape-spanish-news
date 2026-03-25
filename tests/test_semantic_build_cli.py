import sys

import pytest

from scripts.build_semantic_map import (
    _artifact_paths,
    _canonicalize_semantic_records,
    _summary_line,
    parse_args,
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


def _embedding(article_id: int, source: str, title: str, vector: list[float]) -> EmbeddingArtifact:
    return EmbeddingArtifact(
        article_id=article_id,
        source=source,
        title=title,
        url=f"https://e/{article_id}",
        published_at="",
        section="",
        summary_snippet="",
        text_length=1,
        embedding_model="test",
        embedding=vector,
    )


def test_canonicalize_semantic_records_keeps_complete_qualifying_clusters_together() -> None:
    embeddings = [
        _embedding(1, "solo", "A", [1.0, 0.0]),
        _embedding(2, "elpais", "B", [0.0, 1.0]),
        _embedding(3, "elmundo", "C", [0.5, 0.5]),
        _embedding(4, "solo2", "D", [0.2, 0.8]),
    ]
    points = [
        PointArtifact(article_id=1, source="solo", title="A", url="https://e/1", published_at=""),
        PointArtifact(article_id=2, source="elpais", title="B", url="https://e/2", published_at=""),
        PointArtifact(article_id=3, source="elmundo", title="C", url="https://e/3", published_at=""),
        PointArtifact(article_id=4, source="solo2", title="D", url="https://e/4", published_at=""),
    ]
    priority_group = type(
        "Group",
        (),
        {"cluster_id": 7, "article_count": 2, "article_ids": [2, 3]},
    )()

    aligned_embeddings, aligned_points = _canonicalize_semantic_records(
        embeddings,
        points,
        limit=3,
        projection_set="pca_2d_latest",
        priority_groups=[priority_group],
    )

    assert [record.article_id for record in aligned_points] == [2, 3, 1]
    assert [record.article_id for record in aligned_embeddings] == [2, 3, 1]


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


def test_parse_args_accepts_temporal_window_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_semantic_map.py",
            "--days-back",
            "2",
            "--date-from",
            "2026-03-10",
            "--date-to",
            "2026-03-12",
        ],
    )

    args = parse_args()

    assert args.days_back == 2
    assert args.date_from == "2026-03-10"
    assert args.date_to == "2026-03-12"
