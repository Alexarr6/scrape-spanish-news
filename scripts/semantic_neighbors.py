from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.persistence.db import create_postgres_engine, make_session, resolve_db_url  # noqa: E402
from src.semantic.dbstore import load_seed_article, nearest_neighbors  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Return nearest semantic neighbors for an article")
    parser.add_argument("--db-url", default="")
    parser.add_argument("--article-id", type=int, required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="json_mode")
    parser.add_argument("--include-seed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_postgres_engine(resolve_db_url(args.db_url))
    with make_session(engine) as session:
        seed = load_seed_article(session, article_id=args.article_id)
        rows = nearest_neighbors(session, article_id=args.article_id, limit=args.limit)

    if args.json_mode:
        payload = {
            "seed": seed.__dict__ if seed else None,
            "neighbors": [row.__dict__ for row in rows],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.include_seed and seed is not None:
        print(
            "seed "
            f"article_id={seed.article_id} source={seed.source} date={seed.display_date} "
            f"section={seed.section or '-'} model={seed.embedding_model or '-'}"
        )
        print(f"  title={seed.title}")
        print(f"  summary={_clip(seed.summary_snippet)}")
        print(f"  url={seed.url}")

    for index, row in enumerate(rows, start=1):
        print(
            f"{index}. article_id={row.article_id} similarity={row.similarity:.4f} "
            f"source={row.source} date={row.display_date or row.published_date} "
            f"section={row.section or '-'}"
        )
        print(f"   title={row.title}")
        print(f"   summary={_clip(row.summary_snippet)}")
        print(f"   url={row.url}")
    return 0


def _clip(value: str, *, limit: int = 180) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


if __name__ == "__main__":
    raise SystemExit(main())
