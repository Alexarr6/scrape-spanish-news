from __future__ import annotations

import pytest

from src.analysis.shared.contracts import ArticleEnrichmentPayload


def test_enrichment_payload_rejects_unknown_tag_codes():
    with pytest.raises(ValueError):
        ArticleEnrichmentPayload(
            article_type="news_report",
            article_type_confidence=0.9,
            primary_tag_code="unknown_tag",
        )


def test_enrichment_payload_accepts_bounded_valid_payload():
    payload = ArticleEnrichmentPayload(
        article_type="news_report",
        article_type_confidence=0.9,
        primary_tag_code="politics_national",
        secondary_tag_codes=["justice", "statement_reaction"],
        entities=[],
        key_phrases=["Fiscalía investiga el caso"],
        claims=["La investigación sigue abierta"],
    )

    assert payload.primary_tag_code == "politics_national"
    assert payload.secondary_tag_codes == ["justice", "statement_reaction"]
