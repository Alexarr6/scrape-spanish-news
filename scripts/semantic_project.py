from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.persistence.db import create_postgres_engine, make_session, resolve_db_url  # noqa: E402
from src.semantic.dbstore import (  # noqa: E402
    DEFAULT_PROJECTION_SET,
    load_projected_points,
    refresh_projection_set,
)
from src.semantic.export import write_points_json, write_semantic_map_html  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Rebuild the 2D PCA projection set from persisted embeddings")
    )
    parser.add_argument("--db-url", default="")
    parser.add_argument("--projection-set", default=DEFAULT_PROJECTION_SET)
    parser.add_argument("--out-json", default="")
    parser.add_argument("--out-html", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_postgres_engine(resolve_db_url(args.db_url))
    with make_session(engine) as session:
        total = refresh_projection_set(session, projection_set=args.projection_set)
        points = load_projected_points(session, projection_set=args.projection_set)
    if args.out_json:
        write_points_json(points, Path(args.out_json))
    if args.out_html:
        write_semantic_map_html(points, Path(args.out_html))
    print(f"semantic_project projection_set={args.projection_set} points={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
