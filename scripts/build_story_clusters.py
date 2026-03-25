"""CLI entrypoint for rebuilding same-story clusters from enriched articles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.pipeline import ClusterPipeline  # noqa: E402
from src.persistence.db import (  # noqa: E402
    create_postgres_engine,
    init_schema,
    make_session,
    resolve_db_url,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build same-story clusters from enriched articles")
    parser.add_argument("--db-url", default="")
    parser.add_argument("--days-back", type=int, default=3)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--score-threshold", type=float, default=0.55)
    parser.add_argument(
        "--recall-mode",
        choices=("default", "high_recall"),
        default="default",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_postgres_engine(resolve_db_url(args.db_url))
    init_schema(engine)
    session = make_session(engine)
    try:
        metrics, artifacts = ClusterPipeline(session).build_clusters(
            days_back=args.days_back,
            limit=args.limit,
            score_threshold=args.score_threshold,
            recall_mode=args.recall_mode,
        )
        print(
            json.dumps(
                {
                    "metrics": metrics.model_dump(mode="json"),
                    "accepted_pairs": sum(1 for artifact in artifacts if artifact.accepted),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
