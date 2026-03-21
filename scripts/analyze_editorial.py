"""CLI entrypoint for dedicated article-level editorial analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.llm_client import OpenRouterSettings  # noqa: E402
from src.analysis.pipeline import EditorialAnalysisPipeline  # noqa: E402
from src.persistence.db import (  # noqa: E402
    create_postgres_engine,
    init_schema,
    make_session,
    resolve_db_url,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run dedicated editorial analysis for persisted articles"
    )
    parser.add_argument("--db-url", default="")
    parser.add_argument("--days-back", type=int, default=2)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--reprocess", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_postgres_engine(resolve_db_url(args.db_url))
    init_schema(engine)
    session = make_session(engine)
    try:
        settings = OpenRouterSettings.from_env()
        pipeline = EditorialAnalysisPipeline(session, llm_settings=settings)
        metrics = pipeline.analyze_articles(
            days_back=args.days_back,
            limit=args.limit,
            reprocess=args.reprocess,
        )
        print(json.dumps(metrics.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
