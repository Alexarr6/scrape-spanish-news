from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.analysis.orm_models import ClusterMemberORM, StoryClusterORM
from src.api.v1.articles import get_session
from src.api.v1.semantic import router
from src.persistence.orm import Base


DEFAULT_PROJECTION_SET = "pca_3d_latest"
DEFAULT_PROJECTION_KIND = "pca_3d"


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
            text("""
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
        """)
        )
        conn.execute(
            text("""
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
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE semantic_point_analysis (
                id INTEGER PRIMARY KEY,
                article_id INTEGER NOT NULL,
                projection_set TEXT NOT NULL,
                cluster_id INTEGER,
                cluster_size INTEGER NOT NULL DEFAULT 0,
                is_outlier BOOLEAN NOT NULL DEFAULT FALSE,
                local_density_distance REAL NOT NULL DEFAULT 0,
                source_neighbor_diversity INTEGER NOT NULL DEFAULT 0,
                nearby_sources_json TEXT NOT NULL DEFAULT '[]'
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE semantic_clusters (
                id INTEGER PRIMARY KEY,
                projection_set TEXT NOT NULL,
                cluster_id INTEGER NOT NULL,
                size INTEGER NOT NULL,
                top_sources_json TEXT NOT NULL DEFAULT '{}',
                source_count INTEGER NOT NULL DEFAULT 0,
                source_dominance REAL NOT NULL DEFAULT 0,
                date_min TEXT NOT NULL DEFAULT '',
                date_max TEXT NOT NULL DEFAULT '',
                centroid_x REAL NOT NULL DEFAULT 0,
                centroid_y REAL NOT NULL DEFAULT 0,
                centroid_z REAL NOT NULL DEFAULT 0,
                representative_article_ids_json TEXT NOT NULL DEFAULT '[]'
            )
        """)
        )
        created = datetime(2026, 3, 17, 12, 0).isoformat()
        for article in [
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
        ]:
            conn.execute(
                text("""
                INSERT INTO articles (id, source, title, url, published_at, scraped_at, section, author, summary, article_text, tags)
                VALUES (:id, :source, :title, :url, :published_at, :scraped_at, :section, :author, :summary, :article_text, :tags)
            """),
                article,
            )
        for embedding in [
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
        ]:
            conn.execute(
                text("""
                INSERT INTO article_embeddings (id, article_id, embedding_model, embedding_dim, embedding, content_hash, source_text_chars, summary_snippet)
                VALUES (:id, :article_id, :embedding_model, :embedding_dim, :embedding, :content_hash, :source_text_chars, :summary_snippet)
            """),
                embedding,
            )
        for projection in [
            {
                "id": 21,
                "article_id": 1,
                "embedding_id": 11,
                "projection_set": DEFAULT_PROJECTION_SET,
                "projection_kind": DEFAULT_PROJECTION_KIND,
                "projection_version": "v1",
                "x": 0.25,
                "y": 0.75,
                "z": 0.4,
            },
            {
                "id": 22,
                "article_id": 2,
                "embedding_id": 12,
                "projection_set": DEFAULT_PROJECTION_SET,
                "projection_kind": DEFAULT_PROJECTION_KIND,
                "projection_version": "v1",
                "x": -0.4,
                "y": 0.15,
                "z": -0.2,
            },
        ]:
            conn.execute(
                text("""
                INSERT INTO article_projections (id, article_id, embedding_id, projection_set, projection_kind, projection_version, x, y, z)
                VALUES (:id, :article_id, :embedding_id, :projection_set, :projection_kind, :projection_version, :x, :y, :z)
            """),
                projection,
            )
        for row in [
            {
                "id": 31,
                "article_id": 1,
                "projection_set": DEFAULT_PROJECTION_SET,
                "cluster_id": 1,
                "cluster_size": 1,
                "is_outlier": False,
                "local_density_distance": 0.111,
                "source_neighbor_diversity": 2,
                "nearby_sources_json": '["elpais","elmundo"]',
            },
            {
                "id": 32,
                "article_id": 2,
                "projection_set": DEFAULT_PROJECTION_SET,
                "cluster_id": None,
                "cluster_size": 0,
                "is_outlier": True,
                "local_density_distance": 0.444,
                "source_neighbor_diversity": 1,
                "nearby_sources_json": '["elmundo"]',
            },
        ]:
            conn.execute(
                text("""
                INSERT INTO semantic_point_analysis (id, article_id, projection_set, cluster_id, cluster_size, is_outlier, local_density_distance, source_neighbor_diversity, nearby_sources_json)
                VALUES (:id, :article_id, :projection_set, :cluster_id, :cluster_size, :is_outlier, :local_density_distance, :source_neighbor_diversity, :nearby_sources_json)
            """),
                row,
            )
        conn.execute(
            text("""
            INSERT INTO semantic_clusters (id, projection_set, cluster_id, size, top_sources_json, source_count, source_dominance, date_min, date_max, centroid_x, centroid_y, centroid_z, representative_article_ids_json)
            VALUES (41, :projection_set, 1, 1, '{"elpais": 1}', 1, 1.0, '2026-03-17', '2026-03-17', 0.25, 0.75, 0.4, '[1]')
        """),
            {"projection_set": DEFAULT_PROJECTION_SET},
        )
        conn.execute(
            text("""
            INSERT INTO article_editorial_analysis (
                article_id, article_type, article_type_confidence, bias_label, bias_score, bias_confidence,
                tone_emotional, tone_target, opinionatedness, sensationalism, rhetorical_certainty,
                editorial_applicability, editorial_applicability_reason, provider_failure_class,
                analysis_path, unclear_reasons_json, article_type_status, bias_status, tone_emotional_status, tone_target_status,
                opinionatedness_status, sensationalism_status, rhetorical_certainty_status, framing_status,
                framing_devices_json, evidence_spans_json, diagnostics_json, rationale, analysis_status,
                failure_reason, model_provider, model_name, model_version, prompt_version, schema_version,
                content_hash, source_text_version, analyzed_at
            ) VALUES (
                1, 'news', 0.91, 'center_left', -0.18, 0.62,
                'measured', 'government', 'low', 'low', 'moderate',
                'full', 'general_editorial_content', '',
                'strict_success', '["weak_signal"]', 'resolved', 'resolved', 'resolved', 'resolved',
                'resolved', 'resolved', 'resolved', 'resolved',
                '["institutional_conflict","accountability_frame"]',
                '[{"type":"quote","text":"Texto articulo uno","note":"Lead framing"}]',
                '{"dimension_status":{"bias":"resolved","framing":"resolved"}}',
                'Cobertura principalmente informativa con algo de encuadre institucional.', 'completed',
                '', 'openrouter', 'gpt-test', '', 'v1', 'editorial-analysis-v1',
                'hash-1', 'title_summary_body_v1', :analyzed_at
            )
        """),
            {"analyzed_at": created},
        )

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as seed_session:
        seed_session.add_all(
            [
                StoryClusterORM(
                    id=501,
                    cluster_key="story-501",
                    cluster_type="news_event",
                    status="active",
                    summary_headline="Gobierno y energia",
                    summary_text="Cobertura agrupada del mismo evento.",
                    article_count=1,
                    source_count=1,
                ),
                StoryClusterORM(
                    id=502,
                    cluster_key="story-502",
                    cluster_type="news_event",
                    status="active",
                    summary_headline="Mercados y energia",
                    summary_text="Cobertura agrupada del mismo evento.",
                    article_count=1,
                    source_count=1,
                ),
                ClusterMemberORM(cluster_id=501, article_id=1, membership_score=0.98),
                ClusterMemberORM(cluster_id=502, article_id=2, membership_score=0.97),
            ]
        )
        seed_session.commit()

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


def test_explorer_points_returns_cluster_metadata() -> None:
    client = _build_client()
    response = client.get("/api/v1/semantic/explorer/points")
    payload = response.json()

    assert response.status_code == 200
    assert payload["meta"]["available_clusters"] == [1]
    assert payload["meta"]["cluster_summaries"][0]["cluster_id"] == 1
    assert payload["items"][0]["analysis"]["local_density_distance"] >= 0
    assert payload["items"][0]["analysis"]["nearby_sources"]
    membership_by_article = {
        item["article_id"]: item["analysis"]["story_cluster_ids"] for item in payload["items"]
    }
    assert membership_by_article == {1: [501], 2: [502]}


def test_explorer_points_supports_cluster_and_outlier_filters() -> None:
    client = _build_client()

    cluster_response = client.get("/api/v1/semantic/explorer/points", params={"cluster_id": 1})
    outlier_response = client.get(
        "/api/v1/semantic/explorer/points", params={"outlier_only": "true"}
    )

    assert [item["article_id"] for item in cluster_response.json()["items"]] == [1]
    assert [item["article_id"] for item in outlier_response.json()["items"]] == [2]


def test_explorer_points_supports_story_cluster_scope_filter() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={"sem_story_cluster": 502, "sem_mode": "filter"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["article_id"] for item in payload["items"]] == [2]
    assert payload["items"][0]["analysis"]["story_cluster_ids"] == [502]



def test_explorer_points_supports_story_cluster_highlight_mode() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={"sem_story_cluster": 502, "sem_mode": "highlight"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["story_cluster_metadata_available"] is True
    assert sorted(item["article_id"] for item in payload["items"]) == [1, 2]
    membership_by_article = {
        item["article_id"]: item["analysis"]["story_cluster_ids"] for item in payload["items"]
    }
    assert membership_by_article == {1: [501], 2: [502]}


def test_explorer_points_search_highlight_mode_keeps_broad_dataset() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={"search": "gobierno", "sem_mode": "highlight"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert sorted(item["article_id"] for item in payload["items"]) == [1, 2]


def test_explorer_points_search_filter_mode_still_filters_dataset() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={"search": "gobierno", "sem_mode": "filter"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["article_id"] for item in payload["items"]] == [1]


def test_explorer_filters_returns_available_options() -> None:
    client = _build_client()
    response = client.get("/api/v1/semantic/explorer/filters")

    assert response.status_code == 200
    assert response.json()["available_clusters"] == [1]
    assert response.json()["cluster_summaries"][0]["cluster_id"] == 1


def test_explorer_article_detail_returns_analysis_fields(monkeypatch) -> None:
    client = _build_client()
    monkeypatch.setattr(
        "src.semantic.dbstore.nearest_neighbors", lambda _session, article_id, limit: []
    )

    response = client.get("/api/v1/semantic/explorer/articles/1")
    payload = response.json()

    assert response.status_code == 200
    assert payload["semantic_summary"]["cluster_id"] == 1
    assert payload["semantic_summary"]["nearby_sources"] == ["elmundo", "elpais"]
    assert payload["editorial"]["analysis_status"] == "completed"
    assert payload["editorial"]["editorial_applicability"] == "full"
    assert payload["editorial"]["review_flags"]["low_confidence"] is False
    assert payload["editorial"]["evidence_spans"][0]["type"] == "quote"
    assert payload["editorial"]["diagnostics_summary"]["dimension_status"]["bias"] == "resolved"


def test_explorer_article_detail_treats_missing_editorial_row_as_pending(monkeypatch) -> None:
    client = _build_client()
    monkeypatch.setattr(
        "src.semantic.dbstore.nearest_neighbors", lambda _session, article_id, limit: []
    )

    response = client.get("/api/v1/semantic/explorer/articles/2")
    payload = response.json()

    assert response.status_code == 200
    assert payload["editorial"]["analysis_status"] == "pending"
    assert payload["editorial"]["review_flags"]["pending_analysis"] is True
    assert payload["editorial"]["editorial_applicability"] == "full"


def test_explorer_article_detail_returns_404_for_missing_article() -> None:
    client = _build_client()
    response = client.get("/api/v1/semantic/explorer/articles/999")
    assert response.status_code == 404
