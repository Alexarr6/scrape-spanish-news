from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from src.api.v1 import articles, clusters, editorial, semantic
from src.persistence.db import create_postgres_engine, init_schema, make_session, resolve_db_url


def create_app(db_url: str | None = None) -> FastAPI:
    """Create the FastAPI app, initialize base schema, and wire shared DB sessions."""

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
    app.include_router(clusters.router)
    app.include_router(editorial.router)
    app.include_router(semantic.router)
    _mount_frontend_if_built(app)
    return app


def _mount_frontend_if_built(app: FastAPI) -> None:
    """Mount the built frontend only when `frontend/dist` exists."""

    dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    assets_dir = dist_dir / "assets"
    index_file = dist_dir / "index.html"
    if not index_file.exists():
        return
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="explorer-assets")

    @app.get("/explorer", include_in_schema=False)
    def explorer_index() -> FileResponse:
        return FileResponse(index_file)


# Keep module import side-effect free; run with an app factory:
#   uvicorn src.api.app:create_app --factory
