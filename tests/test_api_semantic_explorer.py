from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.v1.articles import get_session
from src.api.v1.semantic import router
from src.persistence.orm_models import Base


def _build_client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE article_embeddings (
                    id INTEGER PRIMARY KEY,
                    article_id INTEGER NOT NULL,
                    embedding_model TEXT NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    embedding TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    source_text_chars INTEGER NOT NULL,
                    summary_snippet TEXT NOT NULL DEFAULT ''
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE article_projections (
                    id INTEGER PRIMARY KEY,
                    article_id INTEGER NOT NULL,
                    embedding_id INTEGER NOT NULL,
                    projection_set TEXT NOT NULL,
                    projection_kind TEXT NOT NULL,
                    projection_version TEXT NOT NULL,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    z REAL
                )
                """
            )
        )
        created = datetime(2026, 3, 17, 12, 0).isoformat()
        articles = [
            {
                "id": 1,
                "source": "elpais",
                "title": "Gobierno y energia",
                "url": "https://example.com/a1",
                "published_at": created,
                "scraped_at": created,
                "section": "politica",
                "author": "Reporter 1",
                "summary": "Resumen del gobierno",
                "article_text": "Texto articulo uno con contexto suficiente.",
                "tags": "energia,politica",
            },
            {
                "id": 2,
                "source": "elmundo",
                "title": "Mercados y energia",
                "url": "https://example.com/a2",
                "published_at": created,
                "scraped_at": created,
                "section": "economia",
                "author": "Reporter 2",
                "summary": "Resumen del mercado",
                "article_text": "Texto articulo dos con contexto suficiente.",
                "tags": "energia,economia",
            },
        ]
        for article in articles:
            conn.execute(
                text(
                    """
                    INSERT INTO articles (
                        id, source, title, url, published_at, scraped_at, section, author,
                        summary, article_text, tags
                    ) VALUES (
                        :id, :source, :title, :url, :published_at, :scraped_at, :section,
                        :author, :summary, :article_text, :tags
                    )
                    """
                ),
                article,
            )
        embeddings = [
            {
                "id": 11,
                "article_id": 1,
                "embedding_model": "text-embedding-3-small",
                "embedding_dim": 3,
                "embedding": "[0.1,0.2,0.3]",
                "content_hash": "hash-1",
                "source_text_chars": 120,
                "summary_snippet": "Resumen del gobierno",
            },
            {
                "id": 12,
                "article_id": 2,
                "embedding_model": "text-embedding-3-small",
                "embedding_dim": 3,
                "embedding": "[0.2,0.1,0.4]",
                "content_hash": "hash-2",
                "source_text_chars": 140,
                "summary_snippet": "Resumen del mercado",
            },
        ]
        for embedding in embeddings:
            conn.execute(
                text(
                    """
                    INSERT INTO article_embeddings (
                        id, article_id, embedding_model, embedding_dim, embedding,
                        content_hash, source_text_chars, summary_snippet
                    ) VALUES (
                        :id, :article_id, :embedding_model, :embedding_dim, :embedding,
                        :content_hash, :source_text_chars, :summary_snippet
                    )
                    """
                ),
                embedding,
            )
        projections = [
            {
                "id": 21,
                "article_id": 1,
                "embedding_id": 11,
                "projection_set": "pca_2d_latest",
                "projection_kind": "pca_2d",
                "projection_version": "v1",
                "x": 0.25,
                "y": 0.75,
                "z": None,
            },
            {
                "id": 22,
                "article_id": 2,
                "embedding_id": 12,
                "projection_set": "pca_2d_latest",
                "projection_kind": "pca_2d",
                "projection_version": "v1",
                "x": -0.4,
                "y": 0.15,
                "z": None,
            },
        ]
        for projection in projections:
            conn.execute(
                text(
                    """
                    INSERT INTO article_projections (
                        id, article_id, embedding_id, projection_set, projection_kind,
                        projection_version, x, y, z
                    ) VALUES (
                        :id, :article_id, :embedding_id, :projection_set, :projection_kind,
                        :projection_version, :x, :y, :z
                    )
                    """
                ),
                projection,
            )

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router)

    def override_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_explorer_points_returns_filtered_items_and_metadata(monkeypatch) -> None:
    client = _build_client()

    monkeypatch.setattr(
        "src.semantic.dbstore.nearest_neighbors",
        lambda _session, article_id, limit: [],
    )

    response = client.get("/api/v1/semantic/explorer/points", params={"source": "elpais"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["meta"]["returned"] == 1
    assert payload["meta"]["available_sources"] == ["elpais"]
    assert payload["items"][0]["article_id"] == 1
    assert payload["items"][0]["analysis"]["neighbor_count"] == 0


def test_explorer_filters_returns_available_options() -> None:
    client = _build_client()

    response = client.get("/api/v1/semantic/explorer/filters")

    assert response.status_code == 200
    assert response.json() == {
        "projection_set": "pca_2d_latest",
        "available_sources": ["elmundo", "elpais"],
        "available_sections": ["economia", "politica"],
        "available_clusters": [],
    }


def test_explorer_article_detail_returns_detail_and_neighbors(monkeypatch) -> None:
    client = _build_client()

    monkeypatch.setattr(
        "src.semantic.dbstore.nearest_neighbors",
        lambda _session, article_id, limit: [
            type(
                "Row",
                (),
                {
                    "article_id": 2,
                    "similarity": 0.91,
                    "source": "elmundo",
                    "title": "Mercados y energia",
                    "url": "https://example.com/a2",
                    "published_at": "2026-03-17T12:00:00",
                    "published_date": "2026-03-17",
                    "display_date": "2026-03-17",
                    "section": "economia",
                    "summary_snippet": "Resumen del mercado",
                    "to_artifact": lambda self: __import__(
                        "src.semantic.contracts", fromlist=["NeighborArtifact"]
                    ).NeighborArtifact(
                        article_id=2,
                        similarity=0.91,
                        source="elmundo",
                        title="Mercados y energia",
                        url="https://example.com/a2",
                        published_at="2026-03-17T12:00:00",
                        published_date="2026-03-17",
                        display_date="2026-03-17",
                        section="economia",
                        summary_snippet="Resumen del mercado",
                    ),
                },
            )()
        ],
    )

    response = client.get("/api/v1/semantic/explorer/articles/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["article"]["article_id"] == 1
    assert payload["point"]["article_id"] == 1
    assert payload["neighbors"][0]["article_id"] == 2
    assert payload["semantic_summary"]["neighbor_count"] == 1


def test_explorer_article_detail_returns_404_for_missing_article() -> None:
    client = _build_client()

    response = client.get("/api/v1/semantic/explorer/articles/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Semantic explorer article not found"}
