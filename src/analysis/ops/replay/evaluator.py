from __future__ import annotations

import json
from pathlib import Path

from src.analysis.editorial.normalization import (
    EditorialNormalizationError,
    normalize_editorial_payload,
)
from src.analysis.ops.replay.core import FIXTURE_DIR, ReplayCaseFixture, ReplayCaseResult


def load_replay_fixtures(fixtures_dir: Path | None = None) -> list[ReplayCaseFixture]:
    root = fixtures_dir or FIXTURE_DIR
    return [
        ReplayCaseFixture.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(root.glob("*.json"))
    ]


def evaluate_replay_fixture(fixture: ReplayCaseFixture) -> ReplayCaseResult:
    raw_payload = fixture.parsed_json
    if raw_payload is None:
        if fixture.raw_provider_output is None:
            raise ValueError(
                f"fixture {fixture.fixture_id} has neither parsed_json nor raw_provider_output"
            )
        raw_payload = json.loads(_extract_json_block(fixture.raw_provider_output))

    mismatches: list[str] = []
    try:
        normalization = normalize_editorial_payload(raw_payload)
    except EditorialNormalizationError as exc:
        if fixture.expectation.mode != "normalization_error":
            mismatches.append(f"unexpected normalization error: {exc}")
            return ReplayCaseResult(
                fixture_id=fixture.fixture_id,
                family=fixture.family,
                status="fail",
                mode=fixture.expectation.mode,
                error=str(exc),
                mismatches=mismatches,
            )
        if fixture.expectation.error_contains and fixture.expectation.error_contains not in str(
            exc
        ):
            mismatches.append(
                "expected error containing "
                f"{fixture.expectation.error_contains!r}, got {str(exc)!r}"
            )
        return ReplayCaseResult(
            fixture_id=fixture.fixture_id,
            family=fixture.family,
            status="pass" if not mismatches else "fail",
            mode="normalization_error",
            error=str(exc),
            mismatches=mismatches,
        )

    diagnostics = normalization.diagnostics
    final_payload = normalization.final_payload.model_dump(mode="json")
    dimension_status = {name: diag.status for name, diag in diagnostics.dimension_status.items()}

    if fixture.expectation.mode != "success":
        mismatches.append("expected normalization_error but normalization succeeded")
    if fixture.expectation.editorial_applicability and (
        diagnostics.editorial_applicability != fixture.expectation.editorial_applicability
    ):
        mismatches.append(
            "editorial_applicability expected "
            f"{fixture.expectation.editorial_applicability!r} got "
            f"{diagnostics.editorial_applicability!r}"
        )
    if fixture.expectation.editorial_applicability_reason and (
        diagnostics.editorial_applicability_reason
        != fixture.expectation.editorial_applicability_reason
    ):
        mismatches.append(
            "editorial_applicability_reason expected "
            f"{fixture.expectation.editorial_applicability_reason!r} got "
            f"{diagnostics.editorial_applicability_reason!r}"
        )
    if fixture.expectation.final_payload and final_payload != fixture.expectation.final_payload:
        mismatches.append("final_payload mismatch")
    if sorted(normalization.unclear_reasons) != sorted(fixture.expectation.unclear_reasons):
        mismatches.append(
            "unclear_reasons expected "
            f"{fixture.expectation.unclear_reasons!r} got "
            f"{list(normalization.unclear_reasons)!r}"
        )
    for name, expected_status in fixture.expectation.dimension_status.items():
        actual = dimension_status.get(name)
        if actual != expected_status:
            mismatches.append(
                f"dimension {name!r} expected status {expected_status!r} got {actual!r}"
            )
    for group, expected_values in fixture.expectation.preserved_signal_groups.items():
        actual_values = diagnostics.preserved_signals.get(group, [])
        for value in expected_values:
            if value not in actual_values:
                mismatches.append(f"preserved signal {group!r} missing expected value {value!r}")
    for fragment in fixture.expectation.repair_warnings_contains:
        if not any(fragment in warning for warning in normalization.repair_warnings):
            mismatches.append(f"repair warning fragment missing: {fragment!r}")
    for fragment in fixture.expectation.normalization_warnings_contains:
        if not any(fragment in warning for warning in normalization.normalization_warnings):
            mismatches.append(f"normalization warning fragment missing: {fragment!r}")

    return ReplayCaseResult(
        fixture_id=fixture.fixture_id,
        family=fixture.family,
        status="pass" if not mismatches else "fail",
        mode="success",
        editorial_applicability=diagnostics.editorial_applicability,
        editorial_applicability_reason=diagnostics.editorial_applicability_reason,
        unclear_reasons=list(normalization.unclear_reasons),
        dimension_status=dimension_status,
        preserved_signals=diagnostics.preserved_signals,
        final_payload=final_payload,
        diagnostics=diagnostics.model_dump(mode="json"),
        mismatches=mismatches,
    )


def evaluate_replay_corpus(fixtures_dir: Path | None = None) -> list[ReplayCaseResult]:
    return [evaluate_replay_fixture(fixture) for fixture in load_replay_fixtures(fixtures_dir)]


def _extract_json_block(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            inner = "\n".join(lines[1:-1]).strip()
            if inner.lower().startswith("json\n"):
                inner = inner[5:].strip()
            if inner:
                return inner
    return stripped
