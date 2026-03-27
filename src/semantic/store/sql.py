from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session


def parse_vector_text(value: str) -> list[float]:
    stripped = value.strip().strip("[]")
    if not stripped:
        return []
    return [float(part) for part in stripped.split(",")]


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(_format_float(value) for value in values) + "]"


def split_sql(sql_blob: str) -> list[str]:
    return [part.strip() for part in sql_blob.split(";") if part.strip()]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def session_dialect_name(session: Session | Any) -> str:
    bind = getattr(session, "bind", None)
    if bind is None and hasattr(session, "get_bind"):
        try:
            bind = session.get_bind()
        except Exception:
            bind = None
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", "postgresql")


def explorer_published_at_sql(*, dialect_name: str) -> str:
    if dialect_name == "sqlite":
        return """COALESCE(CAST(a.published_at AS TEXT), '') AS published_at,
                   COALESCE(substr(CAST(a.published_at AS TEXT), 1, 10), '') AS published_date,
                   COALESCE(substr(CAST(a.published_at AS TEXT), 1, 10), '') AS display_date"""
    return """COALESCE(
                       to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SSOF'),
                       ''
                   ) AS published_at,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '') AS published_date,
                   COALESCE(to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD'), '') AS display_date"""


def _format_float(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("embedding contains non-finite values")
    return format(float(value), ".12g")

