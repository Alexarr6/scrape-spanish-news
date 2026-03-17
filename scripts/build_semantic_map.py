from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.persistence.db import create_postgres_engine, make_session, resolve_db_url  # noqa: E402
from src.semantic.contracts import SemanticBuildConfig, SemanticMetrics  # noqa: E402
from src.semantic.dbstore import (  # noqa: E402
    DEFAULT_NEIGHBOR_LIMIT,
    DEFAULT_PROJECTION_SET,
    load_embedding_artifacts,
    load_projected_points,
)
from src.semantic.export import (  # noqa: E402
    write_embeddings_jsonl,
    write_metrics,
    write_points_json,
    write_semantic_map_html,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export the offline semantic exploration artifacts from persisted pgvector state"
        )
    )
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--db-url", default="")
    parser.add_argument("--stamp", default="")
    parser.add_argument("--projection-set", default=DEFAULT_PROJECTION_SET)
    parser.add_argument("--neighbor-limit", type=int, default=DEFAULT_NEIGHBOR_LIMIT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--emit-embeddings-only", action="store_true")
    parser.add_argument("--emit-points-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url = resolve_db_url(args.db_url)
    config = SemanticBuildConfig(database_url=database_url, limit=args.limit, stamp=args.stamp)
    metrics = SemanticMetrics(article_limit=config.limit)
    metrics.artifacts = _artifact_paths(config)

    engine = create_postgres_engine(database_url)
    with make_session(engine) as session:
        embeddings = load_embedding_artifacts(session)
        points = load_projected_points(
            session,
            projection_set=args.projection_set,
            include_neighbors=not args.emit_points_only,
            neighbor_limit=args.neighbor_limit,
        )

    metrics.fetched_rows = len(embeddings)
    metrics.eligible_rows = len(embeddings)
    metrics.embedding_model = embeddings[0].embedding_model if embeddings else ""
    metrics.embedding_dimensions = len(embeddings[0].embedding) if embeddings else 0
    metrics.projection_method = "pca_2d"

    if args.limit:
        embeddings = embeddings[: args.limit]
        points = points[: args.limit]

    if args.dry_run:
        metrics.finish()
        write_metrics(metrics, Path(metrics.artifacts["metrics_json"]))
        print(
            "dry_run "
            f"embeddings={len(embeddings)} "
            f"points={len(points)} "
            f"projection_set={args.projection_set}"
        )
        return 0

    write_embeddings_jsonl(embeddings, Path(metrics.artifacts["embeddings_jsonl"]))
    if args.emit_embeddings_only:
        metrics.finish()
        write_metrics(metrics, Path(metrics.artifacts["metrics_json"]))
        print(f"embeddings_only count={len(embeddings)} model={metrics.embedding_model}")
        return 0

    write_points_json(points, Path(metrics.artifacts["points_json"]))
    if not args.emit_points_only:
        write_semantic_map_html(points, Path(metrics.artifacts["map_html"]))

    metrics.finish()
    write_metrics(metrics, Path(metrics.artifacts["metrics_json"]))
    print(
        "semantic_map "
        f"embeddings={len(embeddings)} "
        f"points={len(points)} "
        f"projection_set={args.projection_set} "
        f"html={'yes' if not args.emit_points_only else 'no'}"
    )
    return 0


def _artifact_paths(config: SemanticBuildConfig) -> dict[str, str]:
    out_dir = Path(config.out_dir)
    log_dir = Path(config.log_dir)
    return {
        "embeddings_jsonl": str(out_dir / f"articles_embeddings_{config.stamp}.jsonl"),
        "points_json": str(out_dir / f"articles_points_{config.stamp}.json"),
        "map_html": str(out_dir / f"semantic_map_{config.stamp}.html"),
        "metrics_json": str(log_dir / f"semantic_{config.stamp}_metrics.json"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
