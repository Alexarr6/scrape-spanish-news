from __future__ import annotations

import json

from scripts import semantic_neighbors
from src.semantic.dbstore import NeighborRow, SeedArticleRow


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_semantic_neighbors_json_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        semantic_neighbors, "create_postgres_engine", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(
        semantic_neighbors, "resolve_db_url", lambda value: value or "postgresql://example"
    )
    monkeypatch.setattr(semantic_neighbors, "make_session", lambda _engine: _FakeSession())
    monkeypatch.setattr(
        semantic_neighbors,
        "load_seed_article",
        lambda _session, article_id: SeedArticleRow(
            article_id=article_id,
            source="elpais",
            title="Semilla",
            url="https://example.com/seed",
            published_at="2026-03-17T00:00:00+00:00",
            published_date="2026-03-17",
            display_date="2026-03-17",
            section="espana",
            summary_snippet="resumen semilla",
            embedding_model="text-embedding-3-small",
        ),
    )
    monkeypatch.setattr(
        semantic_neighbors,
        "nearest_neighbors",
        lambda _session, article_id, limit: [
            NeighborRow(
                article_id=2,
                similarity=0.91,
                source="elmundo",
                title="Vecino",
                url="https://example.com/2",
                published_at="2026-03-17T01:00:00+00:00",
                published_date="2026-03-17",
                display_date="2026-03-17",
                section="politica",
                summary_snippet="resumen vecino",
            )
        ],
    )
    monkeypatch.setattr(
        semantic_neighbors,
        "parse_args",
        lambda: semantic_neighbors.argparse.Namespace(
            db_url="",
            article_id=1,
            limit=5,
            json_mode=True,
            include_seed=True,
        ),
    )

    assert semantic_neighbors.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["seed"]["title"] == "Semilla"
    assert payload["neighbors"][0]["article_id"] == 2


def test_semantic_neighbors_human_output_includes_seed_and_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        semantic_neighbors, "create_postgres_engine", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(
        semantic_neighbors, "resolve_db_url", lambda value: value or "postgresql://example"
    )
    monkeypatch.setattr(semantic_neighbors, "make_session", lambda _engine: _FakeSession())
    monkeypatch.setattr(
        semantic_neighbors,
        "load_seed_article",
        lambda _session, article_id: SeedArticleRow(
            article_id=article_id,
            source="elpais",
            title="Semilla",
            url="https://example.com/seed",
            published_at="2026-03-17T00:00:00+00:00",
            published_date="2026-03-17",
            display_date="2026-03-17",
            section="espana",
            summary_snippet="resumen semilla",
            embedding_model="text-embedding-3-small",
        ),
    )
    monkeypatch.setattr(
        semantic_neighbors,
        "nearest_neighbors",
        lambda _session, article_id, limit: [
            NeighborRow(
                article_id=2,
                similarity=0.91,
                source="elmundo",
                title="Vecino",
                url="https://example.com/2",
                published_at="2026-03-17T01:00:00+00:00",
                published_date="2026-03-17",
                display_date="2026-03-17",
                section="politica",
                summary_snippet="resumen vecino",
            )
        ],
    )
    monkeypatch.setattr(
        semantic_neighbors,
        "parse_args",
        lambda: semantic_neighbors.argparse.Namespace(
            db_url="",
            article_id=1,
            limit=5,
            json_mode=False,
            include_seed=True,
        ),
    )

    assert semantic_neighbors.main() == 0
    output = capsys.readouterr().out
    assert "seed article_id=1 source=elpais" in output
    assert "1. article_id=2 similarity=0.9100 source=elmundo" in output
    assert "summary=resumen vecino" in output
