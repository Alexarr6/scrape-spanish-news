from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import urlparse

from src.adapters.url_filters import extract_url_date
from src.core.models import parse_any_date_to_local_date

MATCHING_TIMEZONE = "Europe/Madrid"

NATIONAL_SIGNAL_TERMS = (
    "gobierno",
    "congreso",
    "senado",
    "tribunal",
    "supremo",
    "constitucional",
    "fiscal",
    "fiscalia",
    "fiscalía",
    "ministerio",
    "moncloa",
    "sánchez",
    "sanchez",
    "pp",
    "psoe",
    "vox",
    "sumar",
    "podemos",
    "junts",
    "erc",
    "pnv",
    "bildu",
    "amnist",
    "presupuesto",
    "presupuest",
    "ley",
    "decreto",
    "policía",
    "policia",
    "guardia civil",
    "aemet",
    "renfe",
    "onu",
    "otan",
    "ue",
    "bruselas",
    "irán",
    "iran",
    "israel",
    "gaza",
    "ucran",
    "rusia",
)


@dataclass(frozen=True)
class LocalityPenaltyRule:
    patterns: tuple[str, ...]
    penalty: int = 1


@dataclass(frozen=True)
class SourceDiscoveryProfile:
    seed_feeds: tuple[str, ...] = ()
    seed_sitemaps: tuple[str, ...] = ()
    seed_html_pages: tuple[str, ...] = ()
    include_path_patterns: tuple[str, ...] = ()
    exclude_path_patterns: tuple[str, ...] = ()
    exclude_section_patterns: tuple[str, ...] = ()
    locality_penalty_rules: tuple[LocalityPenaltyRule, ...] = ()
    bucket_rules: dict[str, tuple[str, ...]] = field(default_factory=dict)
    timezone: str = MATCHING_TIMEZONE
    minimum_usable_candidates: int = 24


@dataclass(frozen=True)
class DiscoveredCandidate:
    url: str
    origin: str
    source: str
    feed_pubdate: str = ""
    url_date: date | None = None
    section_hint: str = ""
    title_hint: str = ""


@dataclass(frozen=True)
class CandidateDecision:
    accepted: bool
    reason: str = ""
    scope_score: int = 0
    same_local_day: bool = False
    locality_penalty: int = 0
    freshness_delta_days: int = 9999


def candidate_from_url(*, url: str, origin: str, source: str) -> DiscoveredCandidate:
    return DiscoveredCandidate(
        url=url,
        origin=origin,
        source=source,
        url_date=extract_url_date(url),
    )


def local_date_for_candidate(candidate: DiscoveredCandidate, timezone_name: str) -> str:
    if candidate.feed_pubdate:
        local = parse_any_date_to_local_date(candidate.feed_pubdate, timezone_name)
        if local:
            return local
    if candidate.url_date is not None:
        return candidate.url_date.isoformat()
    return ""


def locality_penalty(
    candidate: DiscoveredCandidate,
    profile: SourceDiscoveryProfile,
) -> int:
    path = _candidate_path(candidate)
    text = " ".join([candidate.title_hint, candidate.section_hint, path]).casefold()
    if any(term in text for term in NATIONAL_SIGNAL_TERMS):
        return 0
    total = 0
    for rule in profile.locality_penalty_rules:
        if any(pattern.casefold() in path for pattern in rule.patterns):
            total += rule.penalty
    return total


def scope_score(candidate: DiscoveredCandidate, profile: SourceDiscoveryProfile) -> int:
    path = _candidate_path(candidate)
    text = " ".join([path, candidate.section_hint, candidate.title_hint]).casefold()
    score = 0
    if any(pattern.casefold() in path for pattern in profile.include_path_patterns):
        score += 4
    if any(pattern.casefold() in text for pattern in _flatten_bucket_rules(profile.bucket_rules)):
        score += 2
    if any(term in text for term in NATIONAL_SIGNAL_TERMS):
        score += 2
    if candidate.origin == "rss":
        score += 1
    return score


def build_candidate_decision(
    *,
    candidate: DiscoveredCandidate,
    profile: SourceDiscoveryProfile,
    target_date: str,
    is_noise: bool,
) -> CandidateDecision:
    if not candidate.url.strip():
        return CandidateDecision(accepted=False, reason="rejected_scope")
    if is_noise:
        return CandidateDecision(accepted=False, reason="rejected_noise")

    path = _candidate_path(candidate)
    text = " ".join([path, candidate.section_hint, candidate.title_hint]).casefold()

    if profile.include_path_patterns and not any(
        pattern.casefold() in path for pattern in profile.include_path_patterns
    ):
        if not any(term in text for term in NATIONAL_SIGNAL_TERMS):
            return CandidateDecision(accepted=False, reason="rejected_scope")

    if any(pattern.casefold() in path for pattern in profile.exclude_path_patterns):
        return CandidateDecision(accepted=False, reason="rejected_scope")
    if any(pattern.casefold() in text for pattern in profile.exclude_section_patterns):
        return CandidateDecision(accepted=False, reason="rejected_article_type")

    local_date = local_date_for_candidate(candidate, profile.timezone)
    same_local_day = bool(target_date and local_date and local_date == target_date)
    freshness_delta_days = _freshness_delta_days(local_date, target_date) if target_date else 0
    if target_date and freshness_delta_days > 3 and candidate.origin != "html":
        return CandidateDecision(
            accepted=False,
            reason="rejected_stale",
            same_local_day=same_local_day,
            freshness_delta_days=freshness_delta_days,
        )

    penalty = locality_penalty(candidate, profile)
    score = scope_score(candidate, profile)
    if penalty >= 3 and score < 4:
        return CandidateDecision(
            accepted=False,
            reason="rejected_locality",
            same_local_day=same_local_day,
            freshness_delta_days=freshness_delta_days,
            locality_penalty=penalty,
            scope_score=score,
        )

    return CandidateDecision(
        accepted=True,
        reason="accepted",
        scope_score=score,
        same_local_day=same_local_day,
        locality_penalty=penalty,
        freshness_delta_days=freshness_delta_days,
    )


def candidate_priority_key(
    candidate: DiscoveredCandidate,
    *,
    target_date: str,
    profile: SourceDiscoveryProfile,
    is_noise: bool,
) -> tuple[int, int, int, int, str]:
    decision = build_candidate_decision(
        candidate=candidate,
        profile=profile,
        target_date=target_date,
        is_noise=is_noise,
    )
    return (
        0 if decision.same_local_day else 1,
        -decision.scope_score,
        decision.freshness_delta_days,
        decision.locality_penalty,
        candidate.url,
    )


def candidate_from_feed_item(source: str, item: dict[str, str]) -> DiscoveredCandidate:
    link = item.get("link", "").strip()
    return DiscoveredCandidate(
        url=link,
        origin="rss",
        source=source,
        feed_pubdate=item.get("pubDate", ""),
        url_date=extract_url_date(link),
        title_hint=item.get("title", ""),
    )


def _candidate_path(candidate: DiscoveredCandidate) -> str:
    return (urlparse(candidate.url).path or "").casefold()


def _flatten_bucket_rules(bucket_rules: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    flattened: list[str] = []
    for patterns in bucket_rules.values():
        flattened.extend(patterns)
    return tuple(flattened)


def _freshness_delta_days(local_date: str, target_date: str) -> int:
    if not local_date:
        return 9999
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
        current = datetime.strptime(local_date, "%Y-%m-%d").date()
    except ValueError:
        return 9999
    return abs((target - current).days)
