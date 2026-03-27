"""Story candidate generation and semantic-neighbor loading helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Literal

from sqlalchemy.exc import SQLAlchemyError

from src.analysis.contracts import CandidateGenerationSummary
from src.analysis.normalization import normalize_lookup

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.analysis.pipeline import CandidatePair, EnrichedArticle


class StoryCandidateGenerator:
    def __init__(self, session: Session | None) -> None:
        self.session = session

    def generate_candidate_pairs(
        self,
        articles: list[EnrichedArticle],
        *,
        max_days_delta: int = 7,
        per_seed_limit: int = 40,
        per_origin_limit: int = 20,
        recall_mode: Literal["default", "high_recall"] = "default",
        semantic_backfill_limit: int = 0,
    ) -> tuple[list[CandidatePair], list[CandidateGenerationSummary]]:
        from src.analysis.pipeline import CandidatePair

        ordered_articles = sorted(articles, key=lambda item: item.article.published_at)
        pair_map: dict[tuple[int, int], CandidatePair] = {}
        summaries: list[CandidateGenerationSummary] = []
        origin_priority = (
            (
                "semantic_neighbor",
                "shared_entity",
                "lexical_neighbor",
                "shared_tag",
                "temporal_window",
            )
            if recall_mode == "high_recall"
            else (
                "temporal_window",
                "shared_tag",
                "shared_entity",
                "semantic_neighbor",
                "lexical_neighbor",
            )
        )
        origin_limits = {origin: per_origin_limit for origin in origin_priority}
        if recall_mode == "high_recall":
            origin_limits.update(
                {
                    "semantic_neighbor": max(per_origin_limit + 10, per_origin_limit),
                    "shared_entity": per_origin_limit,
                    "lexical_neighbor": max(per_origin_limit, 25),
                    "shared_tag": per_origin_limit,
                    "temporal_window": max(12, per_origin_limit // 2),
                }
            )
        semantic_neighbors_by_seed = self.load_semantic_neighbor_candidates(
            ordered_articles,
            max_days_delta=max_days_delta,
            limit=max(
                per_origin_limit * (5 if recall_mode == "high_recall" else 3),
                per_origin_limit,
            ),
        )

        for seed in ordered_articles:
            summary = CandidateGenerationSummary(seed_article_id=seed.article.id)
            candidates: dict[str, list[tuple[int, float]]] = defaultdict(list)
            seed_time = seed.article.published_at
            seed_tags = set(seed.tag_codes)
            seed_entities = set(seed.entity_slugs)
            seed_keyphrases = {
                normalize_lookup(value)
                for value in seed.key_phrases
                if normalize_lookup(value)
            }
            for other in ordered_articles:
                if other.article.id == seed.article.id:
                    continue
                days_delta = abs((seed_time - other.article.published_at).days)
                if days_delta > max_days_delta:
                    continue
                score = max(0.0, 1 - (days_delta / max_days_delta))
                candidates["temporal_window"].append((other.article.id, score))

                shared_tags = seed_tags & set(other.tag_codes)
                if shared_tags:
                    candidates["shared_tag"].append((other.article.id, len(shared_tags) + score))

                shared_entities = seed_entities & set(other.entity_slugs)
                if shared_entities:
                    candidates["shared_entity"].append(
                        (other.article.id, len(shared_entities) + score)
                    )

                other_keyphrases = {
                    normalize_lookup(value)
                    for value in other.key_phrases
                    if normalize_lookup(value)
                }
                lexical_overlap = len(seed_keyphrases & other_keyphrases)
                if lexical_overlap:
                    candidates["lexical_neighbor"].append(
                        (other.article.id, lexical_overlap + score)
                    )
            for article_id, similarity in semantic_neighbors_by_seed.get(seed.article.id, []):
                candidates["semantic_neighbor"].append((article_id, similarity))

            chosen_for_seed: list[int] = []
            seen_ids: set[int] = set()
            ranked_by_origin: dict[str, list[tuple[int, float]]] = {}
            for origin in origin_priority:
                ranked_rows = candidates.get(origin, [])
                if not ranked_rows:
                    continue
                ranked = sorted(ranked_rows, key=lambda item: (-item[1], item[0]))
                ranked_by_origin[origin] = ranked
                origin_limit = origin_limits.get(origin, per_origin_limit)
                summary.origin_counts[origin] = min(len(ranked), origin_limit)
                overflow = max(0, len(ranked) - origin_limit)
                if overflow:
                    summary.overflow_counts[origin] = overflow
                for article_id, _ in ranked[:origin_limit]:
                    if article_id not in seen_ids and len(chosen_for_seed) >= per_seed_limit:
                        summary.overflow_counts[origin] = summary.overflow_counts.get(origin, 0) + 1
                        continue
                    pair_key = tuple(sorted((seed.article.id, article_id)))
                    pair = pair_map.setdefault(
                        pair_key,
                        CandidatePair(
                            left_article_id=pair_key[0],
                            right_article_id=pair_key[1],
                        ),
                    )
                    pair.origins.add(origin)
                    if article_id not in seen_ids:
                        seen_ids.add(article_id)
                        chosen_for_seed.append(article_id)
            if recall_mode == "high_recall" and semantic_backfill_limit > 0:
                backfilled = 0
                for article_id, _ in ranked_by_origin.get("semantic_neighbor", []):
                    if (
                        len(chosen_for_seed) >= per_seed_limit
                        or backfilled >= semantic_backfill_limit
                    ):
                        break
                    if article_id in seen_ids:
                        continue
                    pair_key = tuple(sorted((seed.article.id, article_id)))
                    pair = pair_map.setdefault(
                        pair_key,
                        CandidatePair(
                            left_article_id=pair_key[0],
                            right_article_id=pair_key[1],
                        ),
                    )
                    pair.origins.add("semantic_backfill")
                    seen_ids.add(article_id)
                    chosen_for_seed.append(article_id)
                    backfilled += 1
                if backfilled:
                    summary.origin_counts["semantic_backfill"] = backfilled
            summary.candidate_count = len(chosen_for_seed)
            for rank, article_id in enumerate(chosen_for_seed, start=1):
                pair_key = tuple(sorted((seed.article.id, article_id)))
                pair = pair_map[pair_key]
                if pair.rank is None or rank < pair.rank:
                    pair.rank = rank
            summaries.append(summary)

        pairs = sorted(
            pair_map.values(),
            key=lambda item: (
                item.rank or 999999,
                item.left_article_id,
                item.right_article_id,
            ),
        )
        return pairs, summaries

    def load_semantic_neighbor_candidates(
        self,
        articles: list[EnrichedArticle],
        *,
        max_days_delta: int,
        limit: int,
    ) -> dict[int, list[tuple[int, float]]]:
        if self.session is None or not articles or limit <= 0:
            return {}
        try:
            from src.semantic.dbstore import nearest_neighbors
        except Exception:
            return {}

        article_by_id = {article.article.id: article for article in articles}
        article_ids = set(article_by_id)
        candidates: dict[int, list[tuple[int, float]]] = {}
        for article in articles:
            try:
                neighbor_rows = nearest_neighbors(
                    self.session,
                    article_id=article.article.id,
                    limit=limit,
                )
            except (AttributeError, RuntimeError, TypeError, SQLAlchemyError):
                return {}

            seed_candidates: list[tuple[int, float]] = []
            for neighbor in neighbor_rows:
                neighbor_id = int(neighbor.article_id)
                if neighbor_id == article.article.id or neighbor_id not in article_ids:
                    continue
                days_delta = abs(
                    (article.article.published_at - article_by_id[neighbor_id].article.published_at).days
                )
                if days_delta > max_days_delta:
                    continue
                seed_candidates.append((neighbor_id, max(0.0, float(neighbor.similarity))))
            if seed_candidates:
                candidates[article.article.id] = seed_candidates
        return candidates
