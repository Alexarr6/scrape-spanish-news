from __future__ import annotations

from src.analysis.ops.replay import (
    evaluate_replay_corpus,
    load_replay_fixtures,
    render_replay_report,
)


def test_editorial_replay_corpus_matches_current_expectations() -> None:
    fixtures = load_replay_fixtures()

    assert len(fixtures) >= 6

    results = evaluate_replay_corpus()

    assert all(result.status == "pass" for result in results)
    by_id = {result.fixture_id: result for result in results}

    assert by_id["accident-bulletin-out-of-domain"].editorial_applicability == "out_of_domain"
    assert by_id["travel-price-roundup-limited"].summary_bucket == "limited"
    assert by_id["procedural-politics-mapping-loss"].summary_bucket == "mapping_loss"
    assert by_id["provider-missing-political-news"].summary_bucket == "mapping_loss"
    assert by_id["dict-framing-normalization-error"].editorial_applicability == "out_of_domain"


def test_editorial_replay_report_includes_operator_facing_buckets() -> None:
    report = render_replay_report(evaluate_replay_corpus())

    assert "Editorial replay corpus:" in report
    assert "Signal bucket counts:" in report
    assert "accident-bulletin-out-of-domain" in report
    assert "provider-missing-political-news" in report
    assert "bucket=mapping_loss" in report
    assert "bucket=out_of_domain" in report
