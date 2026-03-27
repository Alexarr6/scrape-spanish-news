from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.enrichment import AnalysisPipeline  # noqa: E402
from src.persistence.db import (  # noqa: E402
    create_postgres_engine,
    init_schema,
    make_session,
    resolve_db_url,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize analysis schema and seed taxonomy")
    parser.add_argument("--db-url", default="")
    return parser.parse_args()


def main() -> int:
    engine = create_postgres_engine(resolve_db_url(parse_args().db_url))
    init_schema(engine)
    session = make_session(engine)
    try:
        AnalysisPipeline(session).seed_tags()
        print("analysis_schema=ok")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
