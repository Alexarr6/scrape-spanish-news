import json

from src.semantic.contracts import (
    ClusterArtifact,
    NeighborArtifact,
    PointAnalysisArtifact,
    PointArtifact,
    SemanticAnalysisArtifact,
    SemanticMetrics,
)
from src.semantic.export import (
    write_analysis_json,
    write_metrics,
    write_points_json,
    write_semantic_map_html,
)

SAMPLE_POINT = PointArtifact(
    article_id=1,
    source="elpais",
    title="Mapa",
    url="https://example.com/mapa",
    published_at="2026-03-17T00:00:00+00:00",
    published_date="2026-03-17",
    display_date="2026-03-17",
    section="espana",
    summary_snippet="Resumen corto",
    text_length=42,
    embedding_model="text-embedding-3-small",
    x=0.1,
    y=-0.2,
    neighbors=[
        NeighborArtifact(
            article_id=2,
            similarity=0.93,
            source="elmundo",
            title="Vecino",
            url="https://example.com/vecino",
            published_at="2026-03-17T01:00:00+00:00",
            published_date="2026-03-17",
            display_date="2026-03-17",
            section="politica",
            summary_snippet="Otro resumen corto",
        )
    ],
    analysis=PointAnalysisArtifact(
        article_id=1,
        cluster_id=2,
        cluster_size=5,
        is_outlier=False,
        local_density_distance=0.3333,
        source_neighbor_diversity=2,
        nearby_sources=["elpais", "elmundo"],
    ),
)


ANALYSIS = SemanticAnalysisArtifact(
    points=[SAMPLE_POINT.analysis],
    clusters=[
        ClusterArtifact(
            cluster_id=2,
            size=5,
            article_ids=[1, 2, 3, 4, 5],
            representative_article_ids=[1, 2, 3],
            top_sources={"elpais": 2, "elmundo": 2, "abc": 1},
            source_count=3,
            source_dominance=0.4,
            date_min="2026-03-16",
            date_max="2026-03-17",
            centroid_x=0.11,
            centroid_y=-0.04,
        )
    ],
    unclustered_article_ids=[99],
    density_baseline=0.42,
    outlier_count=0,
)


def test_write_points_json_writes_expected_payload(tmp_path) -> None:
    out = tmp_path / "points.json"
    write_points_json([SAMPLE_POINT], out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload[0]["article_id"] == 1
    assert payload[0]["url"] == "https://example.com/mapa"
    assert payload[0]["published_date"] == "2026-03-17"
    assert payload[0]["neighbors"][0]["title"] == "Vecino"
    assert payload[0]["analysis"]["cluster_id"] == 2


def test_write_analysis_json_writes_cluster_summary(tmp_path) -> None:
    out = tmp_path / "analysis.json"
    write_analysis_json(ANALYSIS, out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["clusters"][0]["cluster_id"] == 2
    assert payload["clusters"][0]["top_sources"]["elpais"] == 2
    assert payload["points"][0]["source_neighbor_diversity"] == 2


def test_write_metrics_writes_json(tmp_path) -> None:
    out = tmp_path / "metrics.json"
    metrics = SemanticMetrics(article_limit=5, fetched_rows=5, eligible_rows=4)
    metrics.finish()
    write_metrics(metrics, out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["article_limit"] == 5
    assert payload["eligible_rows"] == 4
    assert payload["finished_at"]


def test_write_semantic_map_html_contains_analysis_filters_and_inspector(tmp_path) -> None:
    out = tmp_path / "map.html"
    write_semantic_map_html([SAMPLE_POINT], out)

    html = out.read_text(encoding="utf-8")
    assert "semantic-map" in html
    assert "semantic-inspector" in html
    assert "semantic-search" in html
    assert "semantic-cluster-filter" in html
    assert "Show outliers only" in html
    assert "Nearest semantic neighbors" in html
    assert "Nearby source mix" in html
    assert "Open original article" in html
    assert "outliers=${matches.length}" not in html
    assert "outliers=${outliers}" in html
    assert "example.com/vecino" in html
