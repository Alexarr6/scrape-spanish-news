from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from src.analysis.clustering.candidates import StoryCandidateGenerator
from src.analysis.clustering.closure import StoryClosureBuilder
from src.analysis.clustering.loading import load_enriched_articles
from src.analysis.clustering.persistence import persist_clusters
from src.analysis.clustering.scoring import StoryPairScorer
from src.analysis.shared.contracts import (
    CandidateGenerationSummary,
    ClusterRebuildMetrics,
    PairScoreArtifact,
)
from src.analysis.shared.types import CandidatePair, EnrichedArticle


class ClusterPipeline:
    """Rebuild same-story clusters from enriched article state."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._active_recall_mode: Literal["default", "high_recall"] = "default"
        self._candidate_generator = StoryCandidateGenerator(session)
        self._pair_scorer = StoryPairScorer()

    def build_clusters(
        self,
        *,
        days_back: int = 3,
        limit: int = 200,
        score_threshold: float = 0.55,
        recall_mode: Literal["default", "high_recall"] = "default",
        corpus: Literal["raw", "matching"] = "matching",
    ) -> tuple[ClusterRebuildMetrics, list[PairScoreArtifact]]:
        started = datetime.now(UTC)
        articles = self._load_enriched_articles(days_back=days_back, limit=limit, corpus=corpus)
        metrics = ClusterRebuildMetrics(article_count=len(articles), started_at=started)
        article_by_id = {article.article.id: article for article in articles}
        artifacts: list[PairScoreArtifact] = []
        accepted_edges: list[tuple[int, int, Any]] = []
        with self._recall_mode_scope(recall_mode):
            candidate_kwargs: dict[str, Any] = {}
            if recall_mode == "high_recall":
                candidate_kwargs = {
                    "max_days_delta": 7,
                    "per_seed_limit": 80,
                    "per_origin_limit": 30,
                    "semantic_backfill_limit": 20,
                }
            candidate_pairs, candidate_summaries = self._generate_candidate_pairs(
                articles,
                recall_mode=recall_mode,
                **candidate_kwargs,
            )
            for summary in candidate_summaries:
                for origin, count in summary.origin_counts.items():
                    metrics.candidate_origin_counts[origin] = (
                        metrics.candidate_origin_counts.get(origin, 0) + count
                    )
                for origin, count in summary.overflow_counts.items():
                    metrics.candidate_overflow_counts[origin] = (
                        metrics.candidate_overflow_counts.get(origin, 0) + count
                    )
            for candidate in candidate_pairs:
                left = article_by_id[candidate.left_article_id]
                right = article_by_id[candidate.right_article_id]
                metrics.candidate_pair_count += 1
                reason = self.score_pair(left, right)
                accepted = reason.hard_block is None and reason.score >= score_threshold
                artifacts.append(
                    PairScoreArtifact(
                        left_article_id=left.article.id,
                        right_article_id=right.article.id,
                        accepted=accepted,
                        candidate_origins=sorted(candidate.origins),
                        candidate_rank=candidate.rank,
                        reason=reason,
                    )
                )
                if accepted:
                    metrics.accepted_pair_count += 1
                    edge_class = self._classify_closure_edge(reason)
                    if edge_class == "strong":
                        metrics.accepted_strong_pair_count += 1
                    else:
                        metrics.accepted_medium_pair_count += 1
                    if reason.risky_bridge_pair:
                        metrics.accepted_risky_pair_count += 1
                    accepted_edges.append((left.article.id, right.article.id, reason))
                else:
                    metrics.rejected_pair_count += 1
            raw_components = self._raw_connected_components(
                [article.article.id for article in articles],
                accepted_edges,
            )
            metrics.raw_component_count = len(raw_components)
            metrics.raw_multi_article_component_count = len(
                [component for component in raw_components if len(component) > 1]
            )
            components, member_closure_meta = self._build_guarded_components(
                [article.article.id for article in articles],
                accepted_edges,
            )
            try:
                self._persist_clusters(articles, components, accepted_edges, member_closure_meta)
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise
            metrics.guarded_cluster_count = len(components)
            metrics.guarded_multi_article_cluster_count = len(
                [component for component in components if len(component) > 1]
            )
            metrics.cluster_count = metrics.guarded_cluster_count
            metrics.singleton_count = len(
                [component for component in components if len(component) == 1]
            )
            metrics.attached_singleton_count = sum(
                1 for meta in member_closure_meta.values() if meta.get("closure_stage") == "attach"
            )
            metrics.unattached_singleton_count = sum(
                1
                for meta in member_closure_meta.values()
                if meta.get("closure_decision") == "no_support"
            )
            metrics.closure_decision_counts = dict(
                Counter(
                    str(meta.get("closure_decision", "unknown"))
                    for meta in member_closure_meta.values()
                )
            )
        metrics.finished_at = datetime.now(UTC)
        return metrics, artifacts

    @contextmanager
    def _recall_mode_scope(self, recall_mode: Literal["default", "high_recall"]) -> Any:
        previous = self._active_recall_mode
        self._active_recall_mode = recall_mode
        try:
            yield
        finally:
            self._active_recall_mode = previous

    def _is_high_recall_mode(self) -> bool:
        return self._active_recall_mode == "high_recall"

    def _story_closure_builder(self) -> StoryClosureBuilder:
        return StoryClosureBuilder(high_recall_mode=self._is_high_recall_mode())

    def _load_enriched_articles(
        self,
        *,
        days_back: int,
        limit: int,
        corpus: Literal["raw", "matching"] = "matching",
    ) -> list[EnrichedArticle]:
        return load_enriched_articles(
            self.session,
            days_back=days_back,
            limit=limit,
            corpus=corpus,
        )

    def _generate_candidate_pairs(
        self,
        articles: list[EnrichedArticle],
        *,
        max_days_delta: int = 7,
        per_seed_limit: int = 40,
        per_origin_limit: int = 20,
        recall_mode: Literal["default", "high_recall"] = "default",
        semantic_backfill_limit: int = 0,
    ) -> tuple[list[CandidatePair], list[CandidateGenerationSummary]]:
        return self._candidate_generator.generate_candidate_pairs(
            articles,
            max_days_delta=max_days_delta,
            per_seed_limit=per_seed_limit,
            per_origin_limit=per_origin_limit,
            recall_mode=recall_mode,
            semantic_backfill_limit=semantic_backfill_limit,
        )

    def score_pair(self, left: EnrichedArticle, right: EnrichedArticle):
        return self._pair_scorer.score_pair(left, right)

    def _connected_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, Any]],
        *,
        recall_mode: Literal["default", "high_recall"] = "default",
    ) -> list[list[int]]:
        with self._recall_mode_scope(recall_mode):
            components, _ = self._build_guarded_components(article_ids, accepted_edges)
        return components

    def _raw_connected_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, Any]],
    ) -> list[list[int]]:
        return self._story_closure_builder().raw_connected_components(article_ids, accepted_edges)

    def _build_guarded_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, Any]],
    ) -> tuple[list[list[int]], dict[int, dict[str, object]]]:
        return self._story_closure_builder().build_guarded_components(article_ids, accepted_edges)

    def _classify_closure_edge(self, reason) -> str:  # type: ignore[no-untyped-def]
        return self._story_closure_builder().classify_closure_edge(reason)

    def _persist_clusters(
        self,
        articles: list[EnrichedArticle],
        components: list[list[int]],
        accepted_edges: list[tuple[int, int, Any]],
        member_closure_meta: dict[int, dict[str, object]],
    ) -> None:
        persist_clusters(
            self.session,
            articles=articles,
            components=components,
            accepted_edges=accepted_edges,
            member_closure_meta=member_closure_meta,
        )
