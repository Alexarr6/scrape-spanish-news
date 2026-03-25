from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.v1.articles import get_session, router
from src.persistence.orm import Base


class TrackingSession(Session):
    closed_sessions: list[bool] = []

    def close(self) -> None:
        self.closed_sessions.append(True)
        super().close()


def _article_payload(title: str = "Title") -> dict[str, object]:
    timestamp = datetime(2026, 3, 15, 12, 0).isoformat()
    return {
        "source": "elpais",
        "title": title,
        "url": "https://elpais.com/a",
        "published_at": timestamp,
        "scraped_at": timestamp,
        "section": "politica",
        "author": "Reporter",
        "summary": "Summary",
        "article_text": "Body",
        "tags": "tag1,tag2",
    }


def _build_client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=TrackingSession, expire_on_commit=False)
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


def test_article_routes_return_200_404_and_close_sessions():
    TrackingSession.closed_sessions = []
    client = _build_client()

    created = client.post("/api/v1/articles", json=_article_payload())
    article_id = created.json()["id"]
    fetched = client.get(f"/api/v1/articles/{article_id}")
    missing = client.get("/api/v1/articles/9999")

    assert created.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["id"] == article_id
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Article not found"}
    assert len(TrackingSession.closed_sessions) == 3


def test_article_routes_return_422_for_invalid_payload_and_params():
    TrackingSession.closed_sessions = []
    client = _build_client()

    invalid_body = client.post("/api/v1/articles", json={"source": "elpais"})
    invalid_param = client.get("/api/v1/articles/not-an-int")

    assert invalid_body.status_code == 422
    assert invalid_param.status_code == 422
    assert len(TrackingSession.closed_sessions) == 2
