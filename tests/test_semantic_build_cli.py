from scripts.build_semantic_map import _artifact_paths, _summary_line
from src.semantic.contracts import ClusterArtifact, PointAnalysisArtifact, PointArtifact, SemanticAnalysisArtifact, SemanticBuildConfig


def test_artifact_paths_include_analysis_json() -> None:
    config = SemanticBuildConfig(database_url="postgresql://example", stamp="20260317-190000")

    artifacts = _artifact_paths(config)

    assert artifacts["analysis_json"].endswith("semantic_analysis_20260317-190000.json")
    assert artifacts["points_json"].endswith("articles_points_20260317-190000.json")


def test_summary_line_reports_cluster_and_outlier_counts() -> None:
    points = [PointArtifact(article_id=1, source="elpais", title="A", url="https://e/1", published_at="")]
    analysis = SemanticAnalysisArtifact(
        points=[PointAnalysisArtifact(article_id=1, cluster_id=2, cluster_size=4)],
        clusters=[ClusterArtifact(cluster_id=2, size=4)],
        outlier_count=1,
    )

    summary = _summary_line(points, analysis, "pca_2d_latest", html=True)

    assert "clusters=1" in summary
    assert "largest_cluster=4" in summary
    assert "outliers=1" in summary
    assert "html=yes" in summary
