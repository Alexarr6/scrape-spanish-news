"""Build and audit the derived hard-news matching corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.matching_corpus import MATCHING_DAILY_CAP, MatchingCorpusPipeline  # noqa: E402
from src.persistence.db import (  # noqa: E402
    create_postgres_engine,
    init_schema,
    make_session,
    resolve_db_url,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the derived hard-news matching corpus")
    parser.add_argument("--db-url", default="")
    parser.add_argument("--days-back", type=int, default=3)
    parser.add_argument("--daily-cap", type=int, default=MATCHING_DAILY_CAP)
    parser.add_argument("--audit-out", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_postgres_engine(resolve_db_url(args.db_url))
    init_schema(engine)
    session = make_session(engine)
    try:
        metrics = MatchingCorpusPipeline(session).build(
            days_back=args.days_back,
            daily_cap=args.daily_cap,
            audit_path=args.audit_out,
        )
        print(json.dumps(metrics.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
