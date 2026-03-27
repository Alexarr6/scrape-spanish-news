from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select  # noqa: E402

from src.analysis.store.models import (  # noqa: E402
    ClusterEntityORM,
    ClusterMemberORM,
    EntityORM,
    StoryClusterORM,
)
from src.persistence.db import (  # noqa: E402
    create_postgres_engine,
    init_schema,
    make_session,
    resolve_db_url,
)
from src.persistence.orm_models import ArticleORM  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a readable story cluster report")
    parser.add_argument("--db-url", default="")
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_postgres_engine(resolve_db_url(args.db_url))
    init_schema(engine)
    session = make_session(engine)
    try:
        clusters = (
            session.execute(
                select(StoryClusterORM)
                .order_by(StoryClusterORM.article_count.desc())
                .limit(args.limit)
            )
            .scalars()
            .all()
        )
        payload: list[dict[str, object]] = []
        for cluster in clusters:
            members = (
                session.execute(
                    select(ArticleORM)
                    .join(ClusterMemberORM, ClusterMemberORM.article_id == ArticleORM.id)
                    .where(ClusterMemberORM.cluster_id == cluster.id)
                )
                .scalars()
                .all()
            )
            entities = session.execute(
                select(EntityORM.canonical_name, ClusterEntityORM.article_coverage_count)
                .join(ClusterEntityORM, ClusterEntityORM.entity_id == EntityORM.id)
                .where(ClusterEntityORM.cluster_id == cluster.id)
                .order_by(ClusterEntityORM.article_coverage_count.desc())
            ).all()
            payload.append(
                {
                    "cluster_key": cluster.cluster_key,
                    "headline": cluster.summary_headline,
                    "article_count": cluster.article_count,
                    "sources": sorted({article.source for article in members}),
                    "articles": [
                        {"id": article.id, "source": article.source, "title": article.title}
                        for article in members
                    ],
                    "top_entities": [
                        {"name": name, "coverage": coverage} for name, coverage in entities[:8]
                    ],
                }
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
