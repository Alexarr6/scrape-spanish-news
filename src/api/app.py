from __future__ import annotations

from collections.abc import Generator

from fastapi import FastAPI
from sqlalchemy.orm import Session

from src.api.v1 import articles, semantic
from src.persistence.db import create_postgres_engine, init_schema, make_session, resolve_db_url


def create_app(db_url: str | None = None) -> FastAPI:
    app = FastAPI(title="Spain News Bias Scraper API", version="1.0.0")

    engine = create_postgres_engine(resolve_db_url(db_url))
    init_schema(engine)

    def _session_dep() -> Generator[Session, None, None]:
        session = make_session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[articles.get_session] = _session_dep
    app.include_router(articles.router)
    app.include_router(semantic.router)
    return app


# Keep module import side-effect free; run with an app factory:
#   uvicorn src.api.app:create_app --factory
