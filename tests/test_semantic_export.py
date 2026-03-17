import json

from src.semantic.contracts import NeighborArtifact, PointArtifact, SemanticMetrics
from src.semantic.export import write_metrics, write_points_json, write_semantic_map_html

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
)


def test_write_points_json_writes_expected_payload(tmp_path) -> None:
    out = tmp_path / "points.json"
    write_points_json([SAMPLE_POINT], out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload[0]["article_id"] == 1
    assert payload[0]["url"] == "https://example.com/mapa"
    assert payload[0]["published_date"] == "2026-03-17"
    assert payload[0]["neighbors"][0]["title"] == "Vecino"


def test_write_metrics_writes_json(tmp_path) -> None:
    out = tmp_path / "metrics.json"
    metrics = SemanticMetrics(article_limit=5, fetched_rows=5, eligible_rows=4)
    metrics.finish()
    write_metrics(metrics, out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["article_limit"] == 5
    assert payload["eligible_rows"] == 4
    assert payload["finished_at"]


def test_write_semantic_map_html_contains_inspector_and_filters(tmp_path) -> None:
    out = tmp_path / "map.html"
    write_semantic_map_html([SAMPLE_POINT], out)

    html = out.read_text(encoding="utf-8")
    assert "semantic-map" in html
    assert "semantic-inspector" in html
    assert "semantic-search" in html
    assert "Nearest semantic neighbors" in html
    assert "Open original article" in html
    assert "Showing ${matches.length}" in html
    assert "example.com/vecino" in html
