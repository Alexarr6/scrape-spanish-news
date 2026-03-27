from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.analysis.store.models import ClusterMemberORM, StoryClusterORM
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
            {
                "id": 3,
                "source": "abc",
                "title": "Opinion fiscal dura",
                "url": "https://example.com/a3",
                "published_at": created,
                "scraped_at": created,
                "section": "opinion",
                "author": "Columnista 3",
                "summary": "Resumen fiscal duro",
                "article_text": "Texto articulo tres con contexto suficiente.",
                "tags": "fiscal,opinion",
            },
            {
                "id": 4,
                "source": "eldiario",
                "title": "Analisis social incompleto",
                "url": "https://example.com/a4",
                "published_at": created,
                "scraped_at": created,
                "section": "sociedad",
                "author": "Reporter 4",
                "summary": "Resumen social",
                "article_text": "Texto articulo cuatro con contexto suficiente.",
                "tags": "sociedad,analisis",
            },
            {
                "id": 5,
                "source": "larazon",
                "title": "Cobertura deportiva ambigua",
                "url": "https://example.com/a5",
                "published_at": created,
                "scraped_at": created,
                "section": "deportes",
                "author": "Reporter 5",
                "summary": "Resumen deportivo",
                "article_text": "Texto articulo cinco con contexto suficiente.",
                "tags": "deportes",
            },
            {
                "id": 6,
                "source": "publico",
                "title": "Editorial cultural fuera de dominio",
                "url": "https://example.com/a6",
                "published_at": created,
                "scraped_at": created,
                "section": "cultura",
                "author": "Reporter 6",
                "summary": "Resumen cultural",
                "article_text": "Texto articulo seis con contexto suficiente.",
                "tags": "cultura,editorial",
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
            {"id": 11, "article_id": 1, "embedding_model": "text-embedding-3-small", "embedding_dim": 3, "embedding": "[0.1,0.2,0.3]", "content_hash": "hash-1", "source_text_chars": 120, "summary_snippet": "Resumen del gobierno"},
            {"id": 12, "article_id": 2, "embedding_model": "text-embedding-3-small", "embedding_dim": 3, "embedding": "[0.2,0.1,0.4]", "content_hash": "hash-2", "source_text_chars": 140, "summary_snippet": "Resumen del mercado"},
            {"id": 13, "article_id": 3, "embedding_model": "text-embedding-3-small", "embedding_dim": 3, "embedding": "[0.3,0.1,0.2]", "content_hash": "hash-3", "source_text_chars": 150, "summary_snippet": "Resumen fiscal duro"},
            {"id": 14, "article_id": 4, "embedding_model": "text-embedding-3-small", "embedding_dim": 3, "embedding": "[0.4,0.2,0.1]", "content_hash": "hash-4", "source_text_chars": 150, "summary_snippet": "Resumen social"},
            {"id": 15, "article_id": 5, "embedding_model": "text-embedding-3-small", "embedding_dim": 3, "embedding": "[0.5,0.2,0.2]", "content_hash": "hash-5", "source_text_chars": 150, "summary_snippet": "Resumen deportivo"},
            {"id": 16, "article_id": 6, "embedding_model": "text-embedding-3-small", "embedding_dim": 3, "embedding": "[0.6,0.2,0.2]", "content_hash": "hash-6", "source_text_chars": 150, "summary_snippet": "Resumen cultural"},
        ]:
            conn.execute(
                text("""
                INSERT INTO article_embeddings (id, article_id, embedding_model, embedding_dim, embedding, content_hash, source_text_chars, summary_snippet)
                VALUES (:id, :article_id, :embedding_model, :embedding_dim, :embedding, :content_hash, :source_text_chars, :summary_snippet)
            """),
                embedding,
            )
        for projection in [
            {"id": 21, "article_id": 1, "embedding_id": 11, "projection_set": DEFAULT_PROJECTION_SET, "projection_kind": DEFAULT_PROJECTION_KIND, "projection_version": "v1", "x": 0.25, "y": 0.75, "z": 0.4},
            {"id": 22, "article_id": 2, "embedding_id": 12, "projection_set": DEFAULT_PROJECTION_SET, "projection_kind": DEFAULT_PROJECTION_KIND, "projection_version": "v1", "x": -0.4, "y": 0.15, "z": -0.2},
            {"id": 23, "article_id": 3, "embedding_id": 13, "projection_set": DEFAULT_PROJECTION_SET, "projection_kind": DEFAULT_PROJECTION_KIND, "projection_version": "v1", "x": 0.5, "y": -0.25, "z": 0.1},
            {"id": 24, "article_id": 4, "embedding_id": 14, "projection_set": DEFAULT_PROJECTION_SET, "projection_kind": DEFAULT_PROJECTION_KIND, "projection_version": "v1", "x": -0.55, "y": -0.15, "z": 0.2},
            {"id": 25, "article_id": 5, "embedding_id": 15, "projection_set": DEFAULT_PROJECTION_SET, "projection_kind": DEFAULT_PROJECTION_KIND, "projection_version": "v1", "x": 0.15, "y": -0.6, "z": -0.1},
            {"id": 26, "article_id": 6, "embedding_id": 16, "projection_set": DEFAULT_PROJECTION_SET, "projection_kind": DEFAULT_PROJECTION_KIND, "projection_version": "v1", "x": -0.15, "y": -0.7, "z": -0.3},
        ]:
            conn.execute(
                text("""
                INSERT INTO article_projections (id, article_id, embedding_id, projection_set, projection_kind, projection_version, x, y, z)
                VALUES (:id, :article_id, :embedding_id, :projection_set, :projection_kind, :projection_version, :x, :y, :z)
            """),
                projection,
            )
        for row in [
            {"id": 31, "article_id": 1, "projection_set": DEFAULT_PROJECTION_SET, "cluster_id": 1, "cluster_size": 1, "is_outlier": False, "local_density_distance": 0.111, "source_neighbor_diversity": 2, "nearby_sources_json": '["elpais","elmundo"]'},
            {"id": 32, "article_id": 2, "projection_set": DEFAULT_PROJECTION_SET, "cluster_id": None, "cluster_size": 0, "is_outlier": True, "local_density_distance": 0.444, "source_neighbor_diversity": 1, "nearby_sources_json": '["elmundo"]'},
            {"id": 33, "article_id": 3, "projection_set": DEFAULT_PROJECTION_SET, "cluster_id": 2, "cluster_size": 1, "is_outlier": False, "local_density_distance": 0.222, "source_neighbor_diversity": 2, "nearby_sources_json": '["abc","elpais"]'},
            {"id": 34, "article_id": 4, "projection_set": DEFAULT_PROJECTION_SET, "cluster_id": 3, "cluster_size": 1, "is_outlier": False, "local_density_distance": 0.333, "source_neighbor_diversity": 2, "nearby_sources_json": '["eldiario","abc"]'},
            {"id": 35, "article_id": 5, "projection_set": DEFAULT_PROJECTION_SET, "cluster_id": 4, "cluster_size": 1, "is_outlier": False, "local_density_distance": 0.555, "source_neighbor_diversity": 1, "nearby_sources_json": '["larazon"]'},
            {"id": 36, "article_id": 6, "projection_set": DEFAULT_PROJECTION_SET, "cluster_id": 5, "cluster_size": 1, "is_outlier": False, "local_density_distance": 0.666, "source_neighbor_diversity": 1, "nearby_sources_json": '["publico"]'},
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
        editorial_insert_sql = text("""
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
                :article_id, :article_type, :article_type_confidence, :bias_label, :bias_score, :bias_confidence,
                :tone_emotional, :tone_target, :opinionatedness, :sensationalism, :rhetorical_certainty,
                :editorial_applicability, :editorial_applicability_reason, '',
                'strict_success', :unclear_reasons_json, 'resolved', 'resolved', 'resolved', 'resolved',
                'resolved', 'resolved', 'resolved', 'resolved',
                '[]', :evidence_spans_json,
                '{"dimension_status":{"bias":"resolved","framing":"resolved"}}',
                :rationale, :analysis_status,
                '', 'openrouter', 'gpt-test', '', 'v1', 'editorial-analysis-v1',
                :content_hash, 'title_summary_body_v1', :analyzed_at
            )
        """)
        for editorial in [
            {
                "article_id": 1,
                "article_type": "news",
                "article_type_confidence": 0.91,
                "bias_label": "center_left",
                "bias_score": -0.18,
                "bias_confidence": 0.62,
                "tone_emotional": "measured",
                "tone_target": "government",
                "opinionatedness": "low",
                "sensationalism": "low",
                "rhetorical_certainty": "moderate",
                "editorial_applicability": "full",
                "editorial_applicability_reason": "general_editorial_content",
                "unclear_reasons_json": '["weak_signal"]',
                "evidence_spans_json": '[{"type":"quote","text":"Texto articulo uno","note":"Lead framing"}]',
                "rationale": "Cobertura principalmente informativa con algo de encuadre institucional.",
                "analysis_status": "completed",
                "content_hash": "hash-1",
                "analyzed_at": created,
            },
            {
                "article_id": 3,
                "article_type": "opinion",
                "article_type_confidence": 0.88,
                "bias_label": "center_left",
                "bias_score": -0.22,
                "bias_confidence": 0.30,
                "tone_emotional": "heated",
                "tone_target": "government",
                "opinionatedness": "high",
                "sensationalism": "low",
                "rhetorical_certainty": "high",
                "editorial_applicability": "full",
                "editorial_applicability_reason": "general_editorial_content",
                "unclear_reasons_json": '[]',
                "evidence_spans_json": '[{"type":"quote","text":"Texto articulo tres","note":"Argumento"}]',
                "rationale": "Tiene etiqueta, pero la confianza es floja.",
                "analysis_status": "completed",
                "content_hash": "hash-3",
                "analyzed_at": created,
            },
            {
                "article_id": 4,
                "article_type": "analysis",
                "article_type_confidence": 0.80,
                "bias_label": "center_left",
                "bias_score": -0.10,
                "bias_confidence": 0.82,
                "tone_emotional": "measured",
                "tone_target": "society",
                "opinionatedness": "medium",
                "sensationalism": "low",
                "rhetorical_certainty": "moderate",
                "editorial_applicability": "limited",
                "editorial_applicability_reason": "partial_editorial_signal",
                "unclear_reasons_json": '[]',
                "evidence_spans_json": '[{"type":"quote","text":"Texto articulo cuatro","note":"Contexto"}]',
                "rationale": "La señal existe pero es limitada.",
                "analysis_status": "completed",
                "content_hash": "hash-4",
                "analyzed_at": created,
            },
            {
                "article_id": 5,
                "article_type": "news",
                "article_type_confidence": 0.70,
                "bias_label": "unclear",
                "bias_score": 0.0,
                "bias_confidence": 0.78,
                "tone_emotional": "measured",
                "tone_target": "sports",
                "opinionatedness": "low",
                "sensationalism": "low",
                "rhetorical_certainty": "low",
                "editorial_applicability": "full",
                "editorial_applicability_reason": "general_editorial_content",
                "unclear_reasons_json": '["weak_signal"]',
                "evidence_spans_json": '[{"type":"quote","text":"Texto articulo cinco","note":"Ambiguo"}]',
                "rationale": "Sesgo poco claro.",
                "analysis_status": "completed",
                "content_hash": "hash-5",
                "analyzed_at": created,
            },
            {
                "article_id": 6,
                "article_type": "editorial",
                "article_type_confidence": 0.92,
                "bias_label": "center_left",
                "bias_score": -0.15,
                "bias_confidence": 0.90,
                "tone_emotional": "measured",
                "tone_target": "culture",
                "opinionatedness": "medium",
                "sensationalism": "low",
                "rhetorical_certainty": "moderate",
                "editorial_applicability": "out_of_domain",
                "editorial_applicability_reason": "out_of_domain",
                "unclear_reasons_json": '[]',
                "evidence_spans_json": '[{"type":"quote","text":"Texto articulo seis","note":"No comparable"}]',
                "rationale": "Fuera de dominio.",
                "analysis_status": "completed",
                "content_hash": "hash-6",
                "analyzed_at": created,
            },
        ]:
            conn.execute(editorial_insert_sql, editorial)

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
    preview_by_article = {item["article_id"]: item["editorial_preview"] for item in payload["items"]}
    assert preview_by_article[1]["article_type"] == "news"
    assert preview_by_article[1]["analysis_status"] == "completed"
    assert preview_by_article[1]["bias_label"] == "center_left"
    assert preview_by_article[1]["bias_confidence"] == 0.62
    assert set(preview_by_article[1].keys()) == {
        "analysis_status",
        "editorial_applicability",
        "article_type",
        "article_type_confidence",
        "bias_label",
        "bias_confidence",
        "review_flags",
    }
    assert preview_by_article[2]["analysis_status"] == "pending"
    assert payload["meta"]["editorial"]["coverage"]["pending"] == 1
    assert payload["meta"]["editorial"]["coverage"]["bias_total_completed"] == 5
    assert payload["meta"]["editorial"]["coverage"]["bias_low_confidence"] == 1
    assert payload["meta"]["editorial"]["coverage"]["bias_unknown"] == 1
    assert payload["meta"]["editorial"]["coverage"]["bias_limited"] == 1
    assert payload["meta"]["editorial"]["coverage"]["bias_out_of_domain"] == 1
    assert any(option == {"value": "news", "count": 2} for option in payload["meta"]["editorial"]["article_type"])
    assert payload["meta"]["editorial"]["bias_label"] == [{"value": "center_left", "count": 1}]
    membership_by_article = {
        item["article_id"]: item["analysis"]["story_cluster_ids"] for item in payload["items"]
    }
    assert membership_by_article == {1: [501], 2: [502], 3: [], 4: [], 5: [], 6: []}


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
    assert sorted(item["article_id"] for item in payload["items"]) == [1, 2, 3, 4, 5, 6]
    membership_by_article = {
        item["article_id"]: item["analysis"]["story_cluster_ids"] for item in payload["items"]
    }
    assert membership_by_article == {1: [501], 2: [502], 3: [], 4: [], 5: [], 6: []}


def test_explorer_points_search_highlight_mode_keeps_broad_dataset() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={"search": "gobierno", "sem_mode": "highlight"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert sorted(item["article_id"] for item in payload["items"]) == [1, 2, 3, 4, 5, 6]


def test_explorer_points_search_filter_mode_still_filters_dataset() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={"search": "gobierno", "sem_mode": "filter"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["article_id"] for item in payload["items"]] == [1]


def test_explorer_points_article_type_filter_mode_narrows_dataset() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={
            "sem_editorial_dim": "article_type",
            "sem_editorial_value": "news",
            "sem_mode": "filter",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["article_id"] for item in payload["items"]] == [5, 1]
    assert all(item["editorial_preview"]["article_type"] == "news" for item in payload["items"])


def test_explorer_points_article_type_highlight_mode_keeps_broad_dataset() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={
            "sem_editorial_dim": "article_type",
            "sem_editorial_value": "news",
            "sem_mode": "highlight",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert sorted(item["article_id"] for item in payload["items"]) == [1, 2, 3, 4, 5, 6]
    preview_by_article = {item["article_id"]: item["editorial_preview"] for item in payload["items"]}
    assert preview_by_article[1]["article_type"] == "news"
    assert preview_by_article[2]["analysis_status"] == "pending"


def test_explorer_points_bias_filter_mode_is_strict_confident_full_match_only() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={
            "sem_editorial_dim": "bias_label",
            "sem_editorial_value": "center_left",
            "sem_mode": "filter",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["article_id"] for item in payload["items"]] == [1]
    assert payload["items"][0]["editorial_preview"]["bias_label"] == "center_left"
    assert payload["items"][0]["editorial_preview"]["bias_confidence"] == 0.62


def test_explorer_points_bias_highlight_mode_keeps_broad_dataset_and_previews_all_points() -> None:
    client = _build_client()

    response = client.get(
        "/api/v1/semantic/explorer/points",
        params={
            "sem_editorial_dim": "bias_label",
            "sem_editorial_value": "center_left",
            "sem_mode": "highlight",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert sorted(item["article_id"] for item in payload["items"]) == [1, 2, 3, 4, 5, 6]
    preview_by_article = {item["article_id"]: item["editorial_preview"] for item in payload["items"]}
    assert preview_by_article[1]["bias_label"] == "center_left"
    assert preview_by_article[3]["review_flags"]["low_confidence"] is True
    assert preview_by_article[4]["editorial_applicability"] == "limited"
    assert preview_by_article[5]["review_flags"]["unclear_bias"] is True
    assert preview_by_article[6]["review_flags"]["out_of_domain"] is True


def test_explorer_filters_returns_available_options() -> None:
    client = _build_client()
    response = client.get("/api/v1/semantic/explorer/filters")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available_clusters"] == [1]
    assert payload["cluster_summaries"][0]["cluster_id"] == 1
    assert payload["editorial"]["coverage"]["pending"] == 1
    assert payload["editorial"]["coverage"]["bias_low_confidence"] == 1
    assert payload["editorial"]["coverage"]["bias_unknown"] == 1
    assert any(option == {"value": "news", "count": 2} for option in payload["editorial"]["article_type"])
    assert payload["editorial"]["bias_label"] == [{"value": "center_left", "count": 1}]


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
