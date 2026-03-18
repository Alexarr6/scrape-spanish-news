from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import text  # noqa: E402

from src.persistence.db import create_postgres_engine, resolve_db_url  # noqa: E402
from src.semantic.dbstore import init_pgvector_schema  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize pgvector-backed semantic tables")
    parser.add_argument("--db-url", default="")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--ensure-ann-index", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_postgres_engine(resolve_db_url(args.db_url))
    init_pgvector_schema(
        engine,
        embedding_model=args.embedding_model,
        ensure_ann_index=args.ensure_ann_index,
    )
    with engine.begin() as conn:
        extension = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        print(f"vector_extension={extension.scalar_one()}")
        print(conn.execute(text("SELECT to_regclass('public.article_embeddings')")).scalar_one())
        print(conn.execute(text("SELECT to_regclass('public.article_projections')")).scalar_one())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
