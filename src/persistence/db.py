from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from src.persistence.orm_models import Base


def resolve_db_url(cli_db_url: str | None = None) -> str:
    db_url = (cli_db_url or os.getenv("DATABASE_URL", "")).strip()
    if not db_url:
        raise ValueError("Database URL is required when --persist is enabled")
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://") :]
    if not db_url.startswith("postgresql"):
        raise ValueError("Postgres-only mode: db URL must start with 'postgresql'")
    if db_url.startswith("postgresql://"):
        db_url = "postgresql+psycopg://" + db_url[len("postgresql://") :]
    return db_url


def create_postgres_engine(db_url: str) -> Engine:
    return create_engine(db_url, future=True)


def init_schema(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)


def make_session(engine: Engine) -> Session:
    return Session(engine)
