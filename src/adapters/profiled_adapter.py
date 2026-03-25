from __future__ import annotations

from src.adapters.discovery_profile import (
    CandidateDecision,
    DiscoveredCandidate,
    SourceDiscoveryProfile,
    build_candidate_decision,
    candidate_from_url,
    candidate_priority_key,
)
from src.adapters.layered_discovery import DiscoveryLayer, run_layered_discovery
from src.adapters.rss_adapter import GenericRSSAdapter
from src.adapters.url_filters import is_probable_noise_url
from src.core.adapter import RunConfig
from src.core.strategies.metrics import build_strategy_metrics_envelope


class ProfiledRSSAdapter(GenericRSSAdapter):
    profile = SourceDiscoveryProfile()

    def __init__(self, http_client=None):
        super().__init__(http_client=http_client)
        self._strategy_metrics: list[dict] = []

    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        urls, metrics = run_layered_discovery(
            cfg=cfg,
            classify=lambda candidate, seen: self._classify_candidate(
                candidate,
                seen=seen,
                target_date=target_date,
            ),
            order_candidates=lambda candidates: self._order_candidates(candidates, target_date),
            layers=[
                DiscoveryLayer(
                    strategy_name="rss_discovery",
                    load_candidates=lambda: self._discover_candidates_from_feeds(
                        list(self.profile.seed_feeds)
                    ),
                ),
                DiscoveryLayer(
                    strategy_name="sitemap_discovery",
                    load_candidates=lambda: self._discover_candidates_from_sitemaps(
                        self._sitemap_seeds()
                    ),
                    should_skip=lambda items: self._has_enough_usable_candidates(
                        items,
                        target_date=target_date,
                        minimum=self.profile.minimum_usable_candidates,
                    ),
                ),
                DiscoveryLayer(
                    strategy_name="html_fallback_discovery",
                    load_candidates=lambda: self._discover_candidates_from_html_pages(
                        list(self.profile.seed_html_pages)
                    ),
                    should_skip=lambda items: self._has_enough_usable_candidates(
                        items,
                        target_date=target_date,
                        minimum=self.profile.minimum_usable_candidates,
                    ),
                ),
            ],
        )
        self._strategy_metrics = metrics
        return urls

    def run(self, target_date: str, cfg: RunConfig):
        articles, metrics = super().run(target_date=target_date, cfg=cfg)
        metrics["strategy_metrics"] = build_strategy_metrics_envelope(self._strategy_metrics)
        return articles, metrics

    def _sitemap_seeds(self) -> list[str]:
        return list(self.profile.seed_sitemaps)

    def _classify_candidate(
        self,
        candidate: str | DiscoveredCandidate,
        *,
        seen: set[str],
        target_date: str,
    ) -> CandidateDecision:
        normalized = self._candidate_from_value(candidate)
        if not normalized.url or normalized.url in seen:
            return CandidateDecision(accepted=False, reason="rejected_scope")
        decision = build_candidate_decision(
            candidate=normalized,
            profile=self.profile,
            target_date=target_date,
            is_noise=self._reject_noise(normalized.url),
        )
        if decision.accepted:
            seen.add(normalized.url)
        return decision

    def _accept(self, link: str | DiscoveredCandidate, seen: set[str]) -> bool:
        return self._classify_candidate(
            link,
            seen=seen,
            target_date="",
        ).accepted

    def _reject_noise(self, link: str) -> bool:
        return is_probable_noise_url(link)

    def _order_candidates(
        self,
        candidates: list[str | DiscoveredCandidate],
        target_date: str,
    ) -> list[DiscoveredCandidate]:
        normalized = [self._candidate_from_value(candidate) for candidate in candidates]
        return sorted(
            normalized,
            key=lambda item: candidate_priority_key(
                item,
                target_date=target_date,
                profile=self.profile,
                is_noise=self._reject_noise(item.url),
            ),
        )

    def _has_enough_usable_candidates(
        self,
        candidates: list[str | DiscoveredCandidate],
        *,
        target_date: str,
        minimum: int,
    ) -> bool:
        usable = 0
        seen: set[str] = set()
        for candidate in candidates:
            decision = self._classify_candidate(candidate, seen=seen, target_date=target_date)
            if decision.accepted and decision.same_local_day:
                usable += 1
            if usable >= minimum:
                return True
        return False

    def _candidate_from_value(self, candidate: str | DiscoveredCandidate) -> DiscoveredCandidate:
        if isinstance(candidate, DiscoveredCandidate):
            return candidate
        return candidate_from_url(url=candidate, origin="legacy", source=self.source)
