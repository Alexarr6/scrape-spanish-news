from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import Session

from src.analysis import orm_models as _analysis_orm_models  # noqa: F401
from src.persistence.orm import Base

EDITORIAL_ADDITIVE_COLUMNS = {
    "provider_failure_class": "VARCHAR(80) NOT NULL DEFAULT ''",
    "unclear_reasons_json": "TEXT NOT NULL DEFAULT '[]'",
    "article_type_status": "VARCHAR(40) NOT NULL DEFAULT ''",
    "bias_status": "VARCHAR(40) NOT NULL DEFAULT ''",
    "tone_emotional_status": "VARCHAR(40) NOT NULL DEFAULT ''",
    "tone_target_status": "VARCHAR(40) NOT NULL DEFAULT ''",
    "opinionatedness_status": "VARCHAR(40) NOT NULL DEFAULT ''",
    "sensationalism_status": "VARCHAR(40) NOT NULL DEFAULT ''",
    "rhetorical_certainty_status": "VARCHAR(40) NOT NULL DEFAULT ''",
    "framing_status": "VARCHAR(40) NOT NULL DEFAULT ''",
}


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
    _ensure_additive_editorial_columns(engine)


def make_session(engine: Engine) -> Session:
    return Session(engine)


def _ensure_additive_editorial_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "article_editorial_analysis" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("article_editorial_analysis")}
    missing = {
        name: ddl for name, ddl in EDITORIAL_ADDITIVE_COLUMNS.items() if name not in existing
    }
    if not missing:
        return
    with engine.begin() as conn:
        for column_name, ddl in missing.items():
            conn.exec_driver_sql(
                f"ALTER TABLE article_editorial_analysis ADD COLUMN {column_name} {ddl}"
            )
