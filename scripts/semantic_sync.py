"""Sync missing or changed article embeddings into the pgvector-backed store."""

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
    DEFAULT_EMBEDDING_MODEL,
    ensure_vector_index,
    resolve_semantic_window,
    select_embedding_candidates,
    upsert_embeddings,
)
from src.semantic.embed import build_embedding_artifacts  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Backfill or incrementally sync article embeddings into pgvector")
    )
    parser.add_argument("--db-url", default="")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--max-chars", type=int, default=12000)
    parser.add_argument("--days-back", type=int, default=None)
    parser.add_argument("--date-from", default="")
    parser.add_argument("--date-to", default="")
    parser.add_argument("--ensure-ann-index", action="store_true")
    parser.add_argument(
        "--prioritize-story-members",
        action="store_true",
        help=(
            "Prioritize recent embeddable members of qualifying story clusters so "
            "cluster coverage completes before plain-recency backlog rows."
        ),
    )
    parser.add_argument(
        "--priority-story-cluster-min-size",
        type=int,
        default=2,
        help=(
            "Minimum story_clusters.article_count that qualifies for semantic "
            "priority (default: 2)"
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Resolve the semantic window, embed candidates, and upsert one sync batch."""

    args = parse_args()
    window = resolve_semantic_window(
        days_back=args.days_back,
        date_from=args.date_from or None,
        date_to=args.date_to or None,
    )
    engine = create_postgres_engine(resolve_db_url(args.db_url))
    config = SemanticBuildConfig(
        database_url=resolve_db_url(args.db_url),
        limit=args.limit,
        batch_size=args.batch_size,
        embedding_model=args.embedding_model,
        max_chars=args.max_chars,
    )
    metrics = SemanticMetrics(article_limit=args.limit)
    with make_session(engine) as session:
        candidates = select_embedding_candidates(
            session,
            limit=args.limit,
            max_chars=args.max_chars,
            embedding_model=args.embedding_model,
            window=window,
            prioritize_story_members=args.prioritize_story_members,
            priority_story_cluster_min_size=args.priority_story_cluster_min_size,
        )
        metrics.fetched_rows = len(candidates)
        if not candidates:
            print("semantic_sync candidates=0 embedded=0")
            return 0
        articles = [candidate.article for candidate in candidates]
        embeddings = build_embedding_artifacts(articles=articles, config=config, metrics=metrics)
        content_hashes = {
            candidate.article.article_id: candidate.content_hash for candidate in candidates
        }
        source_text_chars = {
            candidate.article.article_id: len(candidate.assembled_text) for candidate in candidates
        }
        count = upsert_embeddings(
            session,
            embeddings,
            content_hashes=content_hashes,
            source_text_chars=source_text_chars,
        )
    if args.ensure_ann_index and count:
        ensure_vector_index(engine)
    print(
        "semantic_sync "
        f"candidates={len(candidates)} "
        f"embedded={count} "
        f"requests={metrics.embedding_requests}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
